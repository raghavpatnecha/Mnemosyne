"""
Chat Service - RAG-powered conversational AI
Leverages retrieval endpoint for all search operations
Supports 100+ model providers via LiteLLM
Supports configurable presets and deep reasoning mode
Includes LLM-as-Judge for response validation and correction
"""

import asyncio
import time
from typing import List, Dict, Any, AsyncGenerator, Optional
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime, timezone
import logging

import litellm
from langchain_litellm import ChatLiteLLM
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from backend.models.chat_session import ChatSession
from backend.models.chat_message import ChatMessage
from backend.models.user import User
from backend.config import settings, CHAT_PRESETS
from backend.schemas.chat import (
    RetrievalConfig,
    GenerationConfig,
    Source,
    SourceReference,
    DocumentInfo,
    UsageStats,
    ChatMetadata,
    ChatCompletionResponse,
    StreamChunk,
    ChatPreset,
    ReasoningMode,
    MediaItem,
    FollowUpQuestion,
)
from backend.schemas.retrieval import RetrievalRequest, RetrievalMode
from backend.prompts import PromptBuilder
from backend.services.reasoning_service import DeepReasoningService
from backend.services.judge_service import get_judge_service
from backend.services.followup_service import get_followup_service

# Configure litellm to automatically drop unsupported parameters
litellm.drop_params = True

logger = logging.getLogger(__name__)

# RAG System Prompt - optimized for knowledge-grounded responses
RAG_SYSTEM_PROMPT = """You are a RAG agent with access to a curated knowledge base. Your responses are STRICTLY grounded in retrieved documents.

CORE PRINCIPLES:
1. EVIDENCE-BASED: Every claim must be traceable to a source in the context
2. NO HALLUCINATION: If information is not in the context, explicitly state this
3. SYNTHESIS: Integrate insights from multiple sources, don't just list them
4. CITATION: Use [1], [2], etc. to cite sources inline

RESPONSE PROTOCOL:
1. First, assess what the context DOES contain (your evidence base)
2. Then, identify what the question asks that the context DOES NOT cover (gaps)
3. Answer using ONLY the context, citing sources for each claim
4. If multiple sources support a point, cite all: [1, 2, 3]
5. If sources conflict, acknowledge: "While [1] states X, [2] suggests Y"
6. Clearly state limitations: "The provided documents do not address..."

ABSOLUTE RULES:
- NEVER use your training knowledge to fill gaps in the context
- NEVER fabricate sources or make up information
- If context is empty or irrelevant, respond ONLY with: "I don't have information about this in the provided documents."
- When uncertain, say "Based on the available documents..." not definitive statements"""


class ChatService:
    """
    Chat service using RAG with retrieval endpoint integration

    Key features:
    - Uses /retrievals endpoint for all search operations
    - Supports LightRAG knowledge graph enhancement
    - Hierarchical search with reranking
    - Token counting for usage tracking
    - Multi-turn conversation support
    - Configurable presets (concise, detailed, research, technical, creative)
    - Deep reasoning mode with iterative retrieval
    - Model override support via LiteLLM
    """

    def __init__(self, db: Session):
        """
        Initialize chat service

        Args:
            db: Database session
        """
        self.db = db
        self.llm = self._initialize_llm()
        self.prompt_builder = PromptBuilder()
        self.reasoning_service = DeepReasoningService()
        self.judge_service = get_judge_service()
        self.followup_service = get_followup_service()

    def _initialize_llm(self) -> ChatLiteLLM:
        """Initialize LiteLLM client with configured provider"""
        if settings.LLM_MODEL_STRING:
            model_string = settings.LLM_MODEL_STRING
        else:
            model_string = f"{settings.LLM_PROVIDER}/{settings.CHAT_MODEL}"

        litellm_kwargs = {
            "model": model_string,
            "temperature": settings.CHAT_TEMPERATURE,
            "max_tokens": settings.CHAT_MAX_TOKENS,
            "timeout": settings.LLM_TIMEOUT,
        }

        if settings.LLM_PROVIDER == "openai" or settings.LLM_PROVIDER.startswith("openai"):
            litellm_kwargs["api_key"] = settings.OPENAI_API_KEY

        if settings.LLM_API_BASE:
            litellm_kwargs["api_base"] = settings.LLM_API_BASE

        logger.info(f"Initializing LiteLLM with model: {model_string}")
        return ChatLiteLLM(**litellm_kwargs)

    def _create_llm_for_request(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        preset: str = "detailed",
    ) -> ChatLiteLLM:
        """
        Create LLM instance with request-specific overrides.

        Priority:
        1. Explicit parameters (model, temperature, max_tokens)
        2. Preset defaults
        3. Global config defaults

        Args:
            model: Model override (e.g., "gpt-4o", "claude-3-opus")
            temperature: Temperature override
            max_tokens: Max tokens override
            preset: Preset name for defaults

        Returns:
            Configured ChatLiteLLM instance
        """
        # Get preset configuration
        preset_config = CHAT_PRESETS.get(preset, CHAT_PRESETS["detailed"])

        # Determine model string
        if model:
            # User-specified model (may or may not have provider prefix)
            if "/" not in model and not model.startswith("gpt-") and not model.startswith("o1"):
                # Add default provider prefix if not a known OpenAI model
                model_string = f"{settings.LLM_PROVIDER}/{model}"
            else:
                model_string = model
        elif settings.LLM_MODEL_STRING:
            model_string = settings.LLM_MODEL_STRING
        else:
            model_string = f"{settings.LLM_PROVIDER}/{settings.CHAT_MODEL}"

        # Determine temperature and max_tokens
        final_temp = temperature if temperature is not None else preset_config.get("temperature", settings.CHAT_TEMPERATURE)
        final_max_tokens = max_tokens if max_tokens is not None else preset_config.get("max_tokens", settings.CHAT_MAX_TOKENS)

        litellm_kwargs = {
            "model": model_string,
            "temperature": final_temp,
            "max_tokens": final_max_tokens,
            "timeout": settings.LLM_TIMEOUT,
        }

        # Add API key if needed
        if "openai" in model_string.lower() or model_string.startswith("gpt-") or model_string.startswith("o1"):
            litellm_kwargs["api_key"] = settings.OPENAI_API_KEY

        if settings.LLM_API_BASE:
            litellm_kwargs["api_base"] = settings.LLM_API_BASE

        logger.info(f"Creating LLM for request: model={model_string}, temp={final_temp}, max_tokens={final_max_tokens}")
        return ChatLiteLLM(**litellm_kwargs)

    def _count_tokens(self, text: str, model: str = "gpt-4o-mini") -> int:
        """
        Count tokens in text using tiktoken

        Args:
            text: Text to count tokens for
            model: Model name for encoding selection

        Returns:
            Token count
        """
        try:
            import tiktoken
            try:
                encoding = tiktoken.encoding_for_model(model)
            except KeyError:
                encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except ImportError:
            logger.warning("tiktoken not installed, using word-based estimation")
            return len(text.split()) * 4 // 3

    async def _call_retrieval(
        self,
        query: str,
        user: User,
        collection_id: Optional[UUID],
        config: RetrievalConfig
    ) -> Dict[str, Any]:
        """
        Call retrieval endpoint internally

        Args:
            query: Search query
            user: User object
            collection_id: Optional collection filter
            config: Retrieval configuration

        Returns:
            Retrieval results with sources and graph context
        """
        # DEBUG: Log collection_id at _call_retrieval entry
        logger.info(f"[DEBUG] _call_retrieval received collection_id={collection_id}, enable_graph={config.enable_graph}")

        # Import here to avoid circular dependency
        from backend.api.retrievals import retrieve
        from backend.api.deps import get_cache_service, get_reranker_service, get_query_reformulation_service

        mode_map = {
            "semantic": RetrievalMode.SEMANTIC,
            "keyword": RetrievalMode.KEYWORD,
            "hybrid": RetrievalMode.HYBRID,
            "graph": RetrievalMode.GRAPH
        }

        request = RetrievalRequest(
            query=query,
            mode=mode_map.get(config.mode, RetrievalMode.HYBRID),
            top_k=config.top_k,
            collection_id=collection_id,
            rerank=config.rerank,
            enable_graph=config.enable_graph,
            hierarchical=config.hierarchical,
            expand_context=config.expand_context,
            metadata_filter=config.metadata_filter
        )

        cache = get_cache_service()
        reranker = get_reranker_service()
        reformulator = get_query_reformulation_service()

        response = await retrieve(
            request=request,
            db=self.db,
            current_user=user,
            cache=cache,
            reranker=reranker,
            query_reformulator=reformulator
        )

        logger.debug(f"Retrieval returned {len(response.results)} results, graph_enhanced={response.graph_enhanced}")

        return {
            "results": response.results,
            "graph_enhanced": response.graph_enhanced,
            "graph_context": response.graph_context,
            "graph_references": response.graph_references if hasattr(response, 'graph_references') else []
        }

    def _build_sources(self, retrieval_results: List) -> List[Source]:
        """Convert retrieval results to Source objects"""
        logger.debug(f"Building sources from {len(retrieval_results)} retrieval results")
        sources = []
        for i, r in enumerate(retrieval_results):
            try:
                source = Source(
                    chunk_id=r.chunk_id,
                    content=r.content,
                    chunk_index=r.chunk_index,
                    score=r.score,
                    rerank_score=r.rerank_score,
                    document=DocumentInfo(
                        id=r.document.id,
                        title=r.document.title,
                        filename=r.document.filename
                    ),
                    collection_id=r.collection_id,
                    expanded_content=r.expanded_content,
                    metadata=r.metadata
                )
                sources.append(source)
            except Exception as e:
                logger.error(f"Error building source {i}: {e}, result: {r}")
        logger.debug(f"Built {len(sources)} sources")
        return sources

    def _to_source_references(self, sources: List[Source]) -> List[SourceReference]:
        """Convert full Source objects to lightweight SourceReference for API response"""
        return [
            SourceReference(
                document_id=s.document.id,
                title=s.document.title,
                filename=s.document.filename,
                chunk_index=s.chunk_index,
                score=s.rerank_score if s.rerank_score is not None else s.score
            )
            for s in sources
        ]

    def _graph_refs_to_source_refs(self, graph_references: List) -> List[SourceReference]:
        """
        Convert GraphReference objects to SourceReference format

        GraphReference has: reference_id, file_path, content
        SourceReference needs: document_id, title, filename, chunk_index, score

        Args:
            graph_references: List of GraphReference objects from LightRAG

        Returns:
            List of SourceReference objects
        """
        source_refs = []
        for ref in graph_references:
            # Extract filename from file_path if available
            file_path = getattr(ref, 'file_path', None) or ""
            filename = file_path.split("/")[-1] if file_path else None

            # Use reference_id as document_id, or generate from file_path
            ref_id = getattr(ref, 'reference_id', None)
            if not ref_id and file_path:
                # Use file_path hash as identifier
                import hashlib
                ref_id = hashlib.md5(file_path.encode()).hexdigest()[:36]
            elif not ref_id:
                # Use content hash as fallback
                content = getattr(ref, 'content', None) or ""
                import hashlib
                ref_id = hashlib.md5(content.encode()).hexdigest()[:36]

            source_refs.append(SourceReference(
                document_id=ref_id,
                title=filename or "Knowledge Graph",
                filename=filename,
                chunk_index=0,  # Graph references don't have chunks
                score=1.0  # High relevance for graph context
            ))
        return source_refs

    def _deduplicate_sources(
        self,
        chunk_sources: List[SourceReference],
        graph_sources: List[SourceReference]
    ) -> List[SourceReference]:
        """
        Merge and deduplicate sources from vector chunks and graph references

        Deduplication strategy:
        - Key by (document_id, chunk_index) for uniqueness
        - If duplicate exists, keep the one with higher score
        - Chunk sources come first, then graph sources for tie-breaking

        Args:
            chunk_sources: Sources from vector chunk retrieval
            graph_sources: Sources from LightRAG graph references

        Returns:
            Deduplicated list of SourceReference objects
        """
        seen = {}  # Key: (document_id, filename) -> SourceReference

        # Process chunk sources first (higher priority)
        for source in chunk_sources:
            key = (source.document_id, source.chunk_index)
            if key not in seen:
                seen[key] = source
            elif source.score > seen[key].score:
                seen[key] = source

        # Process graph sources (lower priority, fills gaps)
        for source in graph_sources:
            # For graph sources, also check by filename to catch duplicates
            # when document_id differs but it's the same document
            found_duplicate = False

            for existing_key, existing in list(seen.items()):
                # Match by filename if available
                if (source.filename and existing.filename and
                        source.filename == existing.filename):
                    found_duplicate = True
                    # Only replace if graph source has higher score
                    if source.score > existing.score:
                        seen[existing_key] = source
                    break

            if not found_duplicate:
                key = (source.document_id, source.chunk_index)
                if key not in seen:
                    seen[key] = source
                elif source.score > seen[key].score:
                    seen[key] = source

        # Return sorted by score (highest first)
        deduplicated = sorted(seen.values(), key=lambda x: x.score, reverse=True)

        logger.debug(
            f"Deduplicated sources: {len(chunk_sources)} chunks + "
            f"{len(graph_sources)} graph refs -> {len(deduplicated)} unique"
        )

        return deduplicated

    def _build_context(
        self,
        sources: List[Source],
        graph_context: Optional[str] = None,
        use_expanded: bool = True
    ) -> str:
        """
        Build context string from sources and graph context for LLM prompt

        Args:
            sources: List of source objects
            graph_context: Optional knowledge graph context from LightRAG
            use_expanded: Whether to use expanded_content if available

        Returns:
            Formatted context string combining chunks and graph knowledge
        """
        context_parts = []

        # Add graph context first if available (provides entity/relationship overview)
        if graph_context:
            context_parts.append(
                "KNOWLEDGE GRAPH CONTEXT:\n"
                f"{graph_context}\n"
                "---"
            )

        # Add document chunks
        if sources:
            chunk_parts = []
            for i, source in enumerate(sources, 1):
                content = source.expanded_content if use_expanded and source.expanded_content else source.content
                doc_name = source.document.title or source.document.filename or "Unknown"
                chunk_parts.append(
                    f"[{i}] {content}\n"
                    f"    Source: {doc_name}"
                )
            context_parts.append("DOCUMENT EXCERPTS:\n" + "\n\n".join(chunk_parts))

        return "\n\n".join(context_parts) if context_parts else ""

    def _build_langchain_messages(
        self,
        history: List[ChatMessage],
        user_message: str,
        context: str,
        system_prompt: Optional[str] = None
    ) -> List:
        """
        Build messages for LangChain LLM

        Args:
            history: Conversation history
            user_message: Current user message
            context: Retrieved context
            system_prompt: Optional custom system prompt

        Returns:
            List of LangChain message objects
        """
        messages = [
            SystemMessage(content=system_prompt or RAG_SYSTEM_PROMPT)
        ]

        # Add history (last 10 messages)
        for msg in history[-10:]:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))

        # Add current message with context
        if context:
            content = f"CONTEXT FROM KNOWLEDGE BASE:\n{context}\n\n---\n\nUSER QUESTION: {user_message}"
        else:
            content = user_message

        messages.append(HumanMessage(content=content))
        return messages

    async def chat(
        self,
        session_id: UUID,
        user_message: str,
        user: User,
        collection_id: Optional[UUID] = None,
        retrieval_config: Optional[RetrievalConfig] = None,
        generation_config: Optional[GenerationConfig] = None,
        system_prompt: Optional[str] = None,
        # NEW: Enhanced parameters
        model: Optional[str] = None,
        preset: str = "detailed",
        reasoning_mode: str = "standard",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        custom_instruction: Optional[str] = None,
        is_follow_up: bool = False,
    ) -> ChatCompletionResponse:
        """
        Non-streaming chat with full response

        Args:
            session_id: Chat session ID
            user_message: User's message
            user: User object
            collection_id: Optional collection filter
            retrieval_config: Retrieval configuration
            generation_config: Generation configuration
            system_prompt: Optional custom system prompt
            model: Model override (e.g., "gpt-4o", "claude-3-opus")
            preset: Answer style preset (concise, detailed, research, technical, creative, qna)
            reasoning_mode: Reasoning mode (standard or deep)
            temperature: Temperature override (0.0-2.0)
            max_tokens: Max tokens override
            custom_instruction: Custom instruction to append to the prompt
            is_follow_up: Whether this is a follow-up question (preserves previous context)

        Returns:
            ChatCompletionResponse with full response
        """
        start_time = time.time()
        retrieval_config = retrieval_config or RetrievalConfig()
        generation_config = generation_config or GenerationConfig()

        # Create LLM with request-specific configuration
        llm = self._create_llm_for_request(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            preset=preset,
        )
        model_name = llm.model

        # Get or create session
        session = self._get_or_create_session(session_id, user.id, collection_id, user_message)

        # Save user message
        self._save_message(session_id, "user", user_message)

        # Get history
        history = self._get_history(session_id, limit=10)

        # Call retrieval endpoint
        retrieval_start = time.time()
        retrieval_result = await self._call_retrieval(
            query=user_message,
            user=user,
            collection_id=collection_id,
            config=retrieval_config
        )
        retrieval_latency = int((time.time() - retrieval_start) * 1000)

        # Build sources and context (include graph context in LLM prompt)
        sources = self._build_sources(retrieval_result["results"])
        graph_context_str = retrieval_result["graph_context"] if retrieval_result["graph_enhanced"] else None
        context = self._build_context(sources, graph_context=graph_context_str)

        # Build previous context for follow-up questions
        previous_context = None
        if is_follow_up and history:
            # Extract context from previous assistant messages
            previous_context = self._extract_previous_context(history)

        # Build system prompt using PromptBuilder (preset-aware)
        # Note: PromptBuilder templates include context, so we pass empty context to _build_langchain_messages
        # to avoid duplication. If user provides custom system_prompt, context goes in user message.
        if system_prompt:
            final_system_prompt = system_prompt  # User override takes precedence
            context_for_message = context  # Include context in user message
        else:
            final_system_prompt = self.prompt_builder.build_system_prompt(
                query=user_message,
                chunks=sources,
                preset=preset,
                graph_context=graph_context_str,
                custom_system_prompt=None,
                custom_instruction=custom_instruction,
                is_follow_up=is_follow_up,
                previous_context=previous_context,
            )
            context_for_message = ""  # Context already in system prompt

        # Build messages for LLM
        messages = self._build_langchain_messages(
            history, user_message, context_for_message, final_system_prompt
        )

        # Log the full prompt for debugging
        logger.info("=" * 80)
        logger.info(f"FULL LLM PROMPT (preset={preset}):")
        logger.info("=" * 80)
        for i, msg in enumerate(messages):
            role = msg.__class__.__name__.replace("Message", "").upper()
            logger.info(f"[{role}]:")
            logger.info(msg.content)
            logger.info("-" * 40)
        logger.info("=" * 80)

        # Calculate prompt tokens
        prompt_text = "\n".join([m.content for m in messages])
        prompt_tokens = self._count_tokens(prompt_text, model_name)
        retrieval_tokens = self._count_tokens(context, model_name)

        # Start judge pre-analysis in parallel with generation
        judge_task = None
        if self.judge_service.enabled:
            judge_task = asyncio.create_task(
                self.judge_service.pre_analyze_context(sources, user_message)
            )

        # Generate response using request-specific LLM
        generation_start = time.time()
        response = await llm.ainvoke(messages)
        generation_latency = int((time.time() - generation_start) * 1000)

        response_text = response.content

        # Wait for judge pre-analysis and validate/correct response
        judge_corrected = False
        confidence = 1.0
        if judge_task:
            try:
                analysis = await judge_task
                validation = await self.judge_service.validate_response(
                    response_text, analysis, user_message
                )
                confidence = validation.confidence

                if validation.needs_correction:
                    corrected_text = await self.judge_service.correct_response(
                        response_text, validation, analysis
                    )
                    if corrected_text != response_text:
                        response_text = corrected_text
                        judge_corrected = True
                        logger.info(f"Judge corrected response with {len(validation.issues)} issues")
            except Exception as e:
                logger.warning(f"Judge validation failed: {e}")
                confidence = 0.5

        completion_tokens = self._count_tokens(response_text, model_name)

        # Extract media from sources
        media_items = self.followup_service.extract_media(sources)

        # Generate follow-up questions (runs quickly, typically <1s)
        try:
            followup_result = await self.followup_service.generate_follow_ups(
                query=user_message,
                response=response_text,
                sources=sources,
                media_items=media_items
            )
            follow_up_questions = followup_result.questions
        except Exception as e:
            logger.warning(f"Follow-up generation failed: {e}")
            follow_up_questions = []

        # Save assistant message
        chunk_ids = [s.chunk_id for s in sources]
        self._save_message(
            session_id, "assistant", response_text,
            chunk_ids=chunk_ids,
            metadata={
                "model": model_name,
                "preset": preset,
                "reasoning_mode": reasoning_mode,
                "retrieval_mode": retrieval_config.mode,
                "graph_enhanced": retrieval_result["graph_enhanced"]
            }
        )

        # Update session
        self._update_session(session)

        total_latency = int((time.time() - start_time) * 1000)

        # Convert to lightweight source references for response
        chunk_source_refs = self._to_source_references(sources)

        # Convert graph references to source references
        graph_refs = retrieval_result.get("graph_references", [])
        graph_source_refs = self._graph_refs_to_source_refs(graph_refs)

        logger.info(
            f"Source breakdown: {len(chunk_source_refs)} from chunks, "
            f"{len(graph_source_refs)} from graph ({len(graph_refs)} raw refs)"
        )

        # Deduplicate sources (chunks + graph)
        source_refs = self._deduplicate_sources(chunk_source_refs, graph_source_refs)

        return ChatCompletionResponse(
            query=user_message,
            response=response_text,
            sources=source_refs,
            media=media_items,
            follow_up_questions=follow_up_questions,
            usage=UsageStats(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                retrieval_tokens=retrieval_tokens
            ),
            metadata=ChatMetadata(
                session_id=session_id,
                user_id=user.id,
                collection_id=collection_id,
                retrieval_mode=retrieval_config.mode,
                model=model_name,
                latency_ms=total_latency,
                retrieval_latency_ms=retrieval_latency,
                generation_latency_ms=generation_latency,
                timestamp=datetime.now(timezone.utc),
                confidence=confidence,
                judge_corrected=judge_corrected
            )
        )

    async def chat_stream(
        self,
        session_id: UUID,
        user_message: str,
        user: User,
        collection_id: Optional[UUID] = None,
        retrieval_config: Optional[RetrievalConfig] = None,
        generation_config: Optional[GenerationConfig] = None,
        system_prompt: Optional[str] = None,
        # NEW: Enhanced parameters
        model: Optional[str] = None,
        preset: str = "detailed",
        reasoning_mode: str = "standard",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        custom_instruction: Optional[str] = None,
        is_follow_up: bool = False,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Stream chat response with RAG

        Yields StreamChunk objects with:
        - reasoning_step (for deep reasoning mode)
        - sub_query (for deep reasoning mode)
        - sources (once after retrieval)
        - delta (incremental text)
        - usage (at end)
        - done (completion signal)

        Args:
            session_id: Chat session ID
            user_message: User's message
            user: User object
            collection_id: Optional collection filter
            retrieval_config: Retrieval configuration
            generation_config: Generation configuration
            system_prompt: Optional custom system prompt
            model: Model override (e.g., "gpt-4o", "claude-3-opus")
            preset: Answer style preset (concise, detailed, research, technical, creative)
            reasoning_mode: Reasoning mode (standard or deep)
            temperature: Temperature override (0.0-2.0)
            max_tokens: Max tokens override

        Yields:
            StreamChunk objects
        """
        start_time = time.time()
        retrieval_config = retrieval_config or RetrievalConfig()
        generation_config = generation_config or GenerationConfig()

        # Create LLM with request-specific configuration
        llm = self._create_llm_for_request(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            preset=preset,
        )
        model_name = llm.model

        try:
            # DEBUG: Log collection_id at chat_stream entry
            logger.info(f"[DEBUG] chat_stream received collection_id={collection_id}")

            # Get or create session
            session = self._get_or_create_session(session_id, user.id, collection_id, user_message)

            # Save user message
            self._save_message(session_id, "user", user_message)

            # Get history
            history = self._get_history(session_id, limit=10)

            # Retrieval phase - deep or standard
            retrieval_start = time.time()

            if reasoning_mode == "deep":
                # Deep reasoning: multi-step iterative retrieval
                async for chunk in self.reasoning_service.reason_with_streaming(
                    query=user_message,
                    user=user,
                    collection_id=collection_id,
                    retrieval_config=retrieval_config,
                    call_retrieval_fn=self._call_retrieval,
                    build_sources_fn=self._build_sources,
                ):
                    yield chunk

                # Get result from reasoning service
                reasoning_result = self.reasoning_service.get_last_result()
                sources = reasoning_result.all_sources if reasoning_result else []
                retrieval_result = {
                    "graph_enhanced": False,
                    "graph_context": None,
                    "graph_references": []  # Deep reasoning doesn't use graph refs yet
                }
            else:
                # Standard: single retrieval call
                retrieval_result = await self._call_retrieval(
                    query=user_message,
                    user=user,
                    collection_id=collection_id,
                    config=retrieval_config
                )
                sources = self._build_sources(retrieval_result["results"])

            retrieval_latency = int((time.time() - retrieval_start) * 1000)

            # Build context
            graph_context_str = retrieval_result.get("graph_context") if retrieval_result.get("graph_enhanced") else None
            context = self._build_context(sources, graph_context=graph_context_str)

            # Build previous context for follow-up questions
            previous_context = None
            if is_follow_up and history:
                # Extract context from previous assistant messages
                previous_context = self._extract_previous_context(history)

            # Convert to lightweight source references
            chunk_source_refs = self._to_source_references(sources)

            # Convert graph references to source references
            graph_refs = retrieval_result.get("graph_references", [])
            graph_source_refs = self._graph_refs_to_source_refs(graph_refs)

            logger.info(
                f"Source breakdown: {len(chunk_source_refs)} from chunks, "
                f"{len(graph_source_refs)} from graph ({len(graph_refs)} raw refs)"
            )

            # Deduplicate sources (chunks + graph)
            source_refs = self._deduplicate_sources(chunk_source_refs, graph_source_refs)
            yield StreamChunk(type="sources", sources=source_refs)

            # Extract and yield media items
            media_items = self.followup_service.extract_media(sources)
            if media_items:
                yield StreamChunk(type="media", media=media_items)

            # Start judge pre-analysis in parallel with generation
            judge_task = None
            if self.judge_service.enabled:
                judge_task = asyncio.create_task(
                    self.judge_service.pre_analyze_context(sources, user_message)
                )

            # Build system prompt using PromptBuilder (preset-aware)
            # Note: PromptBuilder templates include context, so we pass empty context to _build_langchain_messages
            # to avoid duplication. If user provides custom system_prompt, context goes in user message.
            if system_prompt:
                final_system_prompt = system_prompt  # User override takes precedence
                context_for_message = context  # Include context in user message
            else:
                final_system_prompt = self.prompt_builder.build_system_prompt(
                    query=user_message,
                    chunks=sources,
                    preset=preset,
                    graph_context=graph_context_str,
                    custom_system_prompt=None,
                    custom_instruction=custom_instruction,
                    is_follow_up=is_follow_up,
                    previous_context=previous_context,
                )
                context_for_message = ""  # Context already in system prompt

            # Build messages for LLM
            messages = self._build_langchain_messages(
                history, user_message, context_for_message, final_system_prompt
            )

            # Log the full prompt for debugging
            logger.info("=" * 80)
            logger.info(f"FULL LLM PROMPT (STREAMING, preset={preset}, reasoning={reasoning_mode}):")
            logger.info("=" * 80)
            for i, msg in enumerate(messages):
                role = msg.__class__.__name__.replace("Message", "").upper()
                logger.info(f"[{role}]:")
                logger.info(msg.content)
                logger.info("-" * 40)
            logger.info("=" * 80)

            # Calculate prompt tokens
            prompt_text = "\n".join([m.content for m in messages])
            prompt_tokens = self._count_tokens(prompt_text, model_name)
            retrieval_tokens = self._count_tokens(context, model_name)

            # Stream response using request-specific LLM
            generation_start = time.time()
            full_response = ""

            async for chunk in llm.astream(messages):
                if chunk.content:
                    delta = chunk.content
                    full_response += delta
                    yield StreamChunk(type="delta", content=delta)

            generation_latency = int((time.time() - generation_start) * 1000)

            # Validate and correct response using judge
            judge_corrected = False
            confidence = 1.0
            if judge_task:
                try:
                    analysis = await judge_task
                    validation = await self.judge_service.validate_response(
                        full_response, analysis, user_message
                    )
                    confidence = validation.confidence

                    if validation.needs_correction:
                        corrected_text = await self.judge_service.correct_response(
                            full_response, validation, analysis
                        )
                        if corrected_text != full_response:
                            # Yield correction as additional delta (replacement)
                            yield StreamChunk(
                                type="delta",
                                content=f"\n\n---\n**[Correction Applied]**\n\n{corrected_text}"
                            )
                            full_response = corrected_text
                            judge_corrected = True
                            logger.info(f"Judge corrected streaming response with {len(validation.issues)} issues")
                except Exception as e:
                    logger.warning(f"Judge validation failed in streaming: {e}")
                    confidence = 0.5

            completion_tokens = self._count_tokens(full_response, model_name)

            # Generate follow-up questions
            try:
                followup_result = await self.followup_service.generate_follow_ups(
                    query=user_message,
                    response=full_response,
                    sources=sources,
                    media_items=media_items
                )
                if followup_result.questions:
                    yield StreamChunk(type="follow_up", follow_up_questions=followup_result.questions)
            except Exception as e:
                logger.warning(f"Follow-up generation failed in streaming: {e}")

            # Save assistant message
            chunk_ids = [s.chunk_id for s in sources]
            self._save_message(
                session_id, "assistant", full_response,
                chunk_ids=chunk_ids,
                metadata={
                    "model": model_name,
                    "preset": preset,
                    "reasoning_mode": reasoning_mode,
                    "retrieval_mode": retrieval_config.mode,
                    "graph_enhanced": retrieval_result.get("graph_enhanced", False)
                }
            )

            # Update session
            self._update_session(session)

            total_latency = int((time.time() - start_time) * 1000)

            # Yield usage stats
            usage = UsageStats(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                retrieval_tokens=retrieval_tokens
            )
            yield StreamChunk(type="usage", usage=usage)

            # Yield done with metadata
            metadata = ChatMetadata(
                session_id=session_id,
                user_id=user.id,
                collection_id=collection_id,
                retrieval_mode=retrieval_config.mode,
                model=model_name,
                latency_ms=total_latency,
                retrieval_latency_ms=retrieval_latency,
                generation_latency_ms=generation_latency,
                timestamp=datetime.now(timezone.utc),
                confidence=confidence,
                judge_corrected=judge_corrected
            )
            yield StreamChunk(type="done", metadata=metadata)

        except Exception as e:
            logger.error(f"Chat stream error: {e}", exc_info=True)
            yield StreamChunk(type="error", error=str(e))

    def _get_or_create_session(
        self,
        session_id: UUID,
        user_id: UUID,
        collection_id: Optional[UUID],
        title_hint: str
    ) -> ChatSession:
        """Get existing session or create new one"""
        session = self.db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id
        ).first()

        if not session:
            session = ChatSession(
                id=session_id,
                user_id=user_id,
                collection_id=collection_id,
                title=title_hint[:100]
            )
            self.db.add(session)
            self.db.commit()

        return session

    def _get_history(self, session_id: UUID, limit: int = 10) -> List[ChatMessage]:
        """Get conversation history"""
        messages = self.db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at.desc()).limit(limit).all()
        return messages[::-1]

    def _extract_previous_context(self, history: List[ChatMessage], max_messages: int = 4) -> str:
        """
        Extract previous context from conversation history for follow-up questions.

        This provides the LLM with a summary of the previous exchange so it can
        build upon what was already discussed.

        Args:
            history: List of ChatMessage objects
            max_messages: Maximum number of recent messages to include

        Returns:
            Formatted string with previous conversation context
        """
        if not history:
            return ""

        # Get the last few exchanges (user questions + assistant answers)
        recent_messages = history[-max_messages:]

        context_parts = []
        for msg in recent_messages:
            role_label = "User" if msg.role == "user" else "Assistant"
            # Truncate long messages to avoid context overflow
            content = msg.content[:1000] + "..." if len(msg.content) > 1000 else msg.content
            context_parts.append(f"{role_label}: {content}")

        if not context_parts:
            return ""

        return "\n\n".join(context_parts)

    def _save_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        chunk_ids: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> ChatMessage:
        """Save a chat message"""
        msg = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            chunk_ids=chunk_ids,
            metadata=metadata
        )
        self.db.add(msg)
        self.db.commit()
        return msg

    def _update_session(self, session: ChatSession):
        """Update session last_message_at"""
        session.last_message_at = datetime.now(timezone.utc)
        self.db.commit()
