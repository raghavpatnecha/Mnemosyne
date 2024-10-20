import json
import asyncio
from datetime import datetime
from typing import List, Dict, AsyncGenerator, Generator, Any
from langchain.callbacks import AsyncIteratorCallbackHandler
from langchain.chains import ConversationChain
from langchain.chains.llm import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatOllama, ChatOpenAI
from langchain_core.callbacks import StreamingStdOutCallbackHandler, CallbackManager
from langchain_core.outputs import LLMResult

from src.service.llm_utils import parse_llm_output, LLMOutput, get_prompt, get_answer_prompt_ollama, \
    process_buffer_line_by_line, get_answer_prompt_openai
from src.config import Config
import logging

logger = logging.getLogger(__name__)
logging.basicConfig()
logger.setLevel(logging.INFO)


class AsyncStreamingCallbackHandler(AsyncIteratorCallbackHandler):
    content: str = ""

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        self.content += token
        await self.queue.put(token)

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        await self.queue.put(None)

class LLMStrategy:
    def __init__(self, config: Config):
        self.config = config

    async def stream_answer_async(self, query: str, context: str, model_name: str, prompt_template: PromptTemplate) -> \
    AsyncGenerator[str, None]:
        pass

    async def _stream_answer_sync(self, query: str, context: str, model_name: str) -> Generator[str, None, None]:
        pass

    async def generate_json(self, query: str, model_name: str, prompt: str) -> dict:
        pass


class OpenAIStrategy(LLMStrategy):
    async def stream_answer_async(self, query: str, context: str, model_name: str, prompt_template: PromptTemplate) -> \
    AsyncGenerator[str, None]:
        callback = AsyncStreamingCallbackHandler()

        gpt_model = ChatOpenAI(
            model_name=model_name,
            temperature=self.config.LLM.TEMPERATURE,
            openai_api_key=self.config.OPENAI.API_KEY,
            streaming=True,
            request_timeout=self.config.LLM.OPENAI_TIMEOUT,
            callbacks=[callback],
        )

        llm_chain = LLMChain(llm=gpt_model, prompt=prompt_template)

        task = asyncio.create_task(llm_chain.arun({"query": query, "context": context}))

        buffer = ""
        in_code_block = False

        async for token in callback.aiter():
            if not token:
                continue

            async for output, new_buffer, new_in_code_block in process_buffer_line_by_line(token, buffer,
                                                                                           in_code_block):
                if output:
                    yield output
                buffer = new_buffer
                in_code_block = new_in_code_block

        # Handle any remaining content
        if buffer.strip():
            if in_code_block:
                yield buffer + "\n```\n"
            else:
                yield buffer.strip() + "\n"

        try:
            await task
        except Exception as e:
            logger.error(f"Error during streaming: {str(e)}")
            raise

    async def _stream_answer_sync(self, query: str, context: str, model_name: str, prompt_template: PromptTemplate) -> Generator[str, None, None]:
        gpt_model = ChatOpenAI(
            model_name=model_name,
            temperature=self.config.LLM.TEMPERATURE,
            openai_api_key=self.config.OPENAI.API_KEY,
            streaming=True,
            request_timeout=self.config.LLM.OPENAI_TIMEOUT,
            callbacks=[StreamingStdOutCallbackHandler()],
        )

        llm_chain = LLMChain(llm=gpt_model, prompt=prompt_template)

        async for chunk in llm_chain.astream({"query": query, "context": context}):
            if chunk and "text" in chunk:
                yield chunk["text"]

    async def generate_json(self, query: str, model_name: str, prompt: str) -> dict:
        gpt_model = ChatOpenAI(
            model_name=model_name,
            temperature=self.config.LLM.TEMPERATURE,
            openai_api_key=self.config.OPENAI.API_KEY,
            request_timeout=self.config.LLM.OPENAI_TIMEOUT,
        )
        conversation_buf = ConversationChain(llm=gpt_model, memory=ConversationBufferMemory())

        output = await conversation_buf.arun(prompt)

        try:
            llm_output = parse_llm_output(output)
            structured_dict = llm_output.dict()
            logger.info(f"OpenAI response for query {query}", extra={
                "model_name": model_name,
                "knowledge_obj": json.dumps(structured_dict)
            })
            return structured_dict
        except ValueError as e:
            logger.error(f"Error processing LLM response: {str(e)}")
            return self.generate_default_response()


class OllamaStrategy(LLMStrategy):
    async def stream_answer_async(self, query: str, context: str, model_name: str, prompt_template: PromptTemplate) -> \
    AsyncGenerator[str, None]:
        callback_handler = AsyncIteratorCallbackHandler()
        gpt_model = ChatOllama(
            model=model_name,
            temperature=self.config.LLM.TEMPERATURE,
            streaming=True,
            callbacks=[callback_handler],
            verbose=True
        )
        llm_chain = LLMChain(llm=gpt_model, prompt=prompt_template)
        task = asyncio.create_task(llm_chain.arun(query=query, context=context))

        buffer = ""
        in_code_block = False

        async for token in callback_handler.aiter():
            if not token:
                continue

            async for output, new_buffer, new_in_code_block in process_buffer_line_by_line(token, buffer,
                                                                                           in_code_block):
                if output:
                    yield output
                buffer = new_buffer
                in_code_block = new_in_code_block

        # Handle any remaining content
        if buffer.strip():
            if in_code_block:
                yield buffer + "\n```\n"
            else:
                yield buffer.strip() + "\n"

        try:
            await task
        except Exception as e:
            logger.error(f"Error during streaming: {str(e)}")
            raise

    async def _stream_answer_sync(self, query: str, context: str, model_name: str, prompt_template: PromptTemplate) -> Generator[str, None, None]:
        prompt_template = PromptTemplate(template=get_answer_prompt_ollama(), input_variables=["query", "context"])
        callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
        gpt_model = ChatOllama(model=model_name, temperature=self.config.LLM.TEMPERATURE, callbacks=callback_manager)
        llm_chain = LLMChain(llm=gpt_model, prompt=prompt_template)
        async for chunk in llm_chain.astream({"query": query, "context": context}):
            if 'text' in chunk:
                content = chunk['text']
                if content:
                    yield content

    async def generate_json(self, query: str, model_name: str, prompt: str) -> dict:
        gpt_model = ChatOllama(
            model=model_name,
            temperature=self.config.LLM.TEMPERATURE,
            request_timeout=self.config.LLM.OPENAI_TIMEOUT
        )

        conversation_buf = ConversationChain(llm=gpt_model, memory=ConversationBufferMemory())

        output = await conversation_buf.arun(prompt)

        try:
            llm_output = parse_llm_output(output)
            structured_dict = llm_output.dict()
            logger.info(f"Ollama response for query {query}", extra={
                "model_name": model_name,
                "knowledge_obj": json.dumps(structured_dict)
            })
            return structured_dict
        except ValueError as e:
            logger.error(f"Error processing LLM response: {str(e)}")
            return self.generate_default_response()

    @staticmethod
    def generate_default_response() -> dict:
        default_response = LLMOutput(
            reason="Failed to parse the response",
            confidence_score=0.0,
            sources=[],
            follow_up=[],
            images=[],
            timestamp=str(datetime.utcnow())
        )
        return default_response.dict()


class LLMStrategyFactory:
    @staticmethod
    def create_strategy(model_name: str, config: Config) -> LLMStrategy:
        if "gpt" in model_name:
            return OpenAIStrategy(config)
        else:
            return OllamaStrategy(config)


class LLMService:
    def __init__(self, config: Config):
        self.config = config

    async def query_knowledge(self, retrieved_info: List[Dict], query: str, model_name: str) -> AsyncGenerator[
        str, None]:
        context = json.dumps(retrieved_info, indent=2)
        strategy = LLMStrategyFactory.create_strategy(model_name, self.config)

        prompt_template = PromptTemplate(
            template=get_answer_prompt_openai() if "gpt" in model_name else get_answer_prompt_ollama(),
            input_variables=["query", "context"]
        )

        # Stream the answer
        #async for chunk in strategy.stream_answer_async(query, context, model_name, prompt_template):
        async for chunk in strategy._stream_answer_sync(query, context, model_name, prompt_template):
            print(chunk)
            yield chunk

        # Generate and yield the full JSON
        full_json = await strategy.generate_json(query, model_name, get_prompt(context, query))
        yield json.dumps(full_json)