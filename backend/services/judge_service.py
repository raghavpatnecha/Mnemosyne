"""
Judge Service - LLM-as-Judge for Response Validation & Correction

Validates LLM responses against retrieved context to detect and correct:
- Fabricated gaps (claiming info is missing when present)
- Hallucinations (facts not in context)
- Relevance issues (not answering the question)
- Completeness issues (missing parts of multi-part questions)
- Missed important information from sources
- Internal contradictions

Runs pre-analysis in parallel with generation to minimize latency.
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from openai import AsyncOpenAI

from backend.config import settings
from backend.schemas.chat import Source

logger = logging.getLogger(__name__)


@dataclass
class ExtractedFact:
    """A single extracted fact from context"""
    value: str
    context: str
    category: str  # dates, names, numbers, claims, responsibilities


@dataclass
class ContextAnalysis:
    """Result of pre-analyzing context for key facts"""
    dates: List[ExtractedFact] = field(default_factory=list)
    names: List[ExtractedFact] = field(default_factory=list)
    numbers: List[ExtractedFact] = field(default_factory=list)
    claims: List[ExtractedFact] = field(default_factory=list)
    responsibilities: List[ExtractedFact] = field(default_factory=list)
    raw_context: str = ""
    query: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for prompt injection"""
        return {
            "dates": [{"value": f.value, "context": f.context} for f in self.dates],
            "names": [{"value": f.value, "context": f.context} for f in self.names],
            "numbers": [{"value": f.value, "context": f.context} for f in self.numbers],
            "claims": [{"value": f.value, "context": f.context} for f in self.claims],
            "responsibilities": [{"value": f.value, "context": f.context} for f in self.responsibilities],
        }

    def has_facts(self) -> bool:
        """Check if any facts were extracted"""
        return bool(self.dates or self.names or self.numbers or self.claims or self.responsibilities)


@dataclass
class Issue:
    """A detected issue in the response"""
    type: str  # FABRICATED_GAP, HALLUCINATION, RELEVANCE, COMPLETENESS, MISSED_INFO, CONTRADICTION
    claim: str  # What the response claimed
    fact: Optional[str] = None  # The actual fact (if applicable)
    correction: Optional[str] = None  # Suggested correction
    severity: str = "medium"  # low, medium, high


@dataclass
class ValidationResult:
    """Result of validating a response"""
    issues: List[Issue] = field(default_factory=list)
    confidence: float = 1.0
    needs_correction: bool = False
    relevance_score: float = 1.0
    completeness_score: float = 1.0
    corrections_text: Optional[str] = None


# Prompts
PRE_ANALYSIS_PROMPT = """Extract key facts from this context that a user might ask about.

CONTEXT:
{context}

USER QUESTION (for relevance):
{query}

Extract ALL factual information, organized by category. Be thorough - missing facts here could cause validation failures.

Output ONLY valid JSON (no markdown, no explanation):
{{
  "dates": [{{"value": "the date/period", "context": "what it refers to"}}],
  "names": [{{"value": "name", "context": "who/what it is"}}],
  "numbers": [{{"value": "number/stat", "context": "what it measures"}}],
  "claims": [{{"value": "factual statement", "context": "source/topic"}}],
  "responsibilities": [{{"value": "role/duty/achievement", "context": "where/when"}}]
}}"""

VALIDATION_PROMPT = """You are a judge validating an LLM response against source facts.

EXTRACTED FACTS FROM CONTEXT:
{analysis_json}

LLM RESPONSE TO VALIDATE:
{response}

ORIGINAL USER QUESTION:
{query}

Check for these issues:

1. FABRICATED_GAP: Response claims information is "not provided/available/mentioned" but it IS in the facts
   - Look for phrases like "not provided", "not mentioned", "no information about", "unavailable"
   - Check if that info actually exists in the extracted facts

2. HALLUCINATION: Response states facts that are NOT in the extracted facts
   - Specific dates, numbers, names that don't match
   - Claims not supported by the facts

3. RELEVANCE: Does the response actually answer the user's question?

4. COMPLETENESS: For multi-part questions, are all parts addressed?

5. MISSED_INFO: Important facts from context that should have been included but weren't

6. CONTRADICTION: Internal contradictions within the response

Output ONLY valid JSON:
{{
  "issues": [
    {{"type": "FABRICATED_GAP", "claim": "what response said", "fact": "actual fact", "correction": "corrected text", "severity": "high"}}
  ],
  "confidence": 0.85,
  "relevance_score": 0.9,
  "completeness_score": 0.8,
  "needs_correction": true
}}

If no issues found, return: {{"issues": [], "confidence": 0.95, "relevance_score": 1.0, "completeness_score": 1.0, "needs_correction": false}}"""

CORRECTION_PROMPT = """Fix the following issues in this response. Make minimal changes - only fix the specific issues identified.

ORIGINAL RESPONSE:
{response}

ISSUES TO FIX:
{issues_json}

AVAILABLE FACTS:
{facts_json}

Rules:
1. Only fix the specific issues listed
2. Preserve the original structure and tone
3. Use the facts to correct fabricated gaps
4. Remove or correct hallucinated information
5. Keep changes minimal and surgical

Output ONLY the corrected response text, nothing else."""


class JudgeService:
    """
    LLM-as-Judge for response validation and correction.

    Runs pre-analysis in parallel with generation for minimal latency impact.
    """

    def __init__(self):
        """Initialize the judge service"""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.enabled = getattr(settings, 'JUDGE_ENABLED', True)
        self.model = getattr(settings, 'JUDGE_MODEL', settings.CHAT_MODEL)
        self.timeout = getattr(settings, 'JUDGE_TIMEOUT', 10)

        logger.info(f"JudgeService initialized: enabled={self.enabled}, model={self.model}")

    async def pre_analyze_context(
        self,
        sources: List[Source],
        query: str
    ) -> ContextAnalysis:
        """
        Extract key facts from context during generation.

        This runs in parallel with LLM generation to minimize latency.

        Args:
            sources: Retrieved source chunks
            query: User's original query

        Returns:
            ContextAnalysis with extracted facts
        """
        if not self.enabled or not sources:
            return ContextAnalysis(query=query)

        # Build context string from sources
        context_parts = []
        for i, source in enumerate(sources, 1):
            content = source.expanded_content or source.content
            doc_name = source.document.title or source.document.filename or "Unknown"
            context_parts.append(f"[{i}] {content}\nSource: {doc_name}")

        context = "\n\n".join(context_parts)

        try:
            prompt = PRE_ANALYSIS_PROMPT.format(context=context, query=query)

            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,  # Low temperature for factual extraction
                    max_completion_tokens=1000,
                    response_format={"type": "json_object"}
                ),
                timeout=self.timeout
            )

            result = json.loads(response.choices[0].message.content)

            analysis = ContextAnalysis(
                dates=[ExtractedFact(value=d["value"], context=d.get("context", ""), category="dates")
                       for d in result.get("dates", [])],
                names=[ExtractedFact(value=n["value"], context=n.get("context", ""), category="names")
                       for n in result.get("names", [])],
                numbers=[ExtractedFact(value=str(n["value"]), context=n.get("context", ""), category="numbers")
                         for n in result.get("numbers", [])],
                claims=[ExtractedFact(value=c["value"], context=c.get("context", ""), category="claims")
                        for c in result.get("claims", [])],
                responsibilities=[ExtractedFact(value=r["value"], context=r.get("context", ""), category="responsibilities")
                                  for r in result.get("responsibilities", [])],
                raw_context=context,
                query=query
            )

            logger.info(
                f"Pre-analysis extracted: {len(analysis.dates)} dates, "
                f"{len(analysis.names)} names, {len(analysis.numbers)} numbers, "
                f"{len(analysis.claims)} claims, {len(analysis.responsibilities)} responsibilities"
            )

            return analysis

        except asyncio.TimeoutError:
            logger.warning(f"Pre-analysis timed out after {self.timeout}s")
            return ContextAnalysis(raw_context=context, query=query)
        except Exception as e:
            logger.error(f"Pre-analysis failed: {e}")
            return ContextAnalysis(raw_context=context, query=query)

    async def validate_response(
        self,
        response: str,
        analysis: ContextAnalysis,
        query: str
    ) -> ValidationResult:
        """
        Validate response against pre-analyzed facts.

        Args:
            response: LLM-generated response to validate
            analysis: Pre-analyzed context facts
            query: Original user query

        Returns:
            ValidationResult with issues and confidence score
        """
        if not self.enabled:
            return ValidationResult(confidence=1.0)

        # If no facts were extracted, can't validate properly
        if not analysis.has_facts():
            logger.info("No facts extracted, skipping validation")
            return ValidationResult(confidence=0.7)  # Lower confidence when can't validate

        try:
            prompt = VALIDATION_PROMPT.format(
                analysis_json=json.dumps(analysis.to_dict(), indent=2),
                response=response,
                query=query
            )

            result = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_completion_tokens=1000,
                    response_format={"type": "json_object"}
                ),
                timeout=self.timeout
            )

            data = json.loads(result.choices[0].message.content)

            issues = [
                Issue(
                    type=i["type"],
                    claim=i["claim"],
                    fact=i.get("fact"),
                    correction=i.get("correction"),
                    severity=i.get("severity", "medium")
                )
                for i in data.get("issues", [])
            ]

            validation = ValidationResult(
                issues=issues,
                confidence=data.get("confidence", 0.8),
                needs_correction=data.get("needs_correction", len(issues) > 0),
                relevance_score=data.get("relevance_score", 1.0),
                completeness_score=data.get("completeness_score", 1.0)
            )

            if issues:
                logger.info(f"Validation found {len(issues)} issues: {[i.type for i in issues]}")
            else:
                logger.info(f"Validation passed with confidence {validation.confidence}")

            return validation

        except asyncio.TimeoutError:
            logger.warning("Validation timed out")
            return ValidationResult(confidence=0.5)
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return ValidationResult(confidence=0.5)

    async def correct_response(
        self,
        response: str,
        validation: ValidationResult,
        analysis: ContextAnalysis
    ) -> str:
        """
        Apply corrections to response based on validation issues.

        Args:
            response: Original response
            validation: Validation result with issues
            analysis: Context analysis with facts

        Returns:
            Corrected response text
        """
        if not validation.needs_correction or not validation.issues:
            return response

        # Filter to high-severity issues worth correcting
        significant_issues = [i for i in validation.issues if i.severity in ["high", "medium"]]

        if not significant_issues:
            return response

        try:
            issues_json = json.dumps([
                {
                    "type": i.type,
                    "claim": i.claim,
                    "fact": i.fact,
                    "correction": i.correction
                }
                for i in significant_issues
            ], indent=2)

            prompt = CORRECTION_PROMPT.format(
                response=response,
                issues_json=issues_json,
                facts_json=json.dumps(analysis.to_dict(), indent=2)
            )

            result = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_completion_tokens=2000
                ),
                timeout=self.timeout
            )

            corrected = result.choices[0].message.content.strip()

            logger.info(f"Applied corrections for {len(significant_issues)} issues")
            return corrected

        except asyncio.TimeoutError:
            logger.warning("Correction timed out, returning original")
            return response
        except Exception as e:
            logger.error(f"Correction failed: {e}")
            return response

    async def judge_response(
        self,
        response: str,
        sources: List[Source],
        query: str
    ) -> tuple[str, ValidationResult]:
        """
        Full judge pipeline: analyze, validate, correct.

        Use this for non-streaming mode or when pre-analysis wasn't done in parallel.

        Args:
            response: LLM response to judge
            sources: Retrieved sources
            query: User query

        Returns:
            Tuple of (corrected_response, validation_result)
        """
        if not self.enabled:
            return response, ValidationResult(confidence=1.0)

        # Pre-analyze context
        analysis = await self.pre_analyze_context(sources, query)

        # Validate response
        validation = await self.validate_response(response, analysis, query)

        # Correct if needed
        if validation.needs_correction:
            corrected = await self.correct_response(response, validation, analysis)
            return corrected, validation

        return response, validation


# Singleton instance
_judge_service: Optional[JudgeService] = None


def get_judge_service() -> JudgeService:
    """Get or create JudgeService singleton"""
    global _judge_service
    if _judge_service is None:
        _judge_service = JudgeService()
    return _judge_service
