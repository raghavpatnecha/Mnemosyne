import json
from typing import List, Optional
from pydantic.v1 import BaseModel, Field, validator
from datetime import datetime

class ImageInfo(BaseModel):
    url: str
    description: str

class ResultInfo(BaseModel):
    title: str
    url: str
    content: str

class LLMOutput(BaseModel):
    reason: str = Field(description="The reason for this answer")
    confidence_score: float = Field(description="The confidence score of the answer")
    sources: Optional[List[ResultInfo]] = Field(default=None, description="Sources referenced for the answer")
    follow_up: List[str] = Field(default_factory=list, description="List of potential follow-up questions")
    images: Optional[List[ImageInfo]] = Field(default=None, description="Images related to the answer")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(),
                           description="Timestamp of when the response was generated")

    @validator('confidence_score')
    def confidence_score_validation(cls, field: float) -> float:
        if not isinstance(field, float) or not 0 <= field <= 1:
            raise ValueError("Confidence score should be a float between 0 and 1")
        return round(field, 5)

    class Config:
        schema_extra = {
            "examples": [
                {
                    "reason": "Example reason",
                    "confidence_score": 0.9,
                    "sources": [
                        {"title": "Example Source", "url": "https://example.com", "content": "Example content"}
                    ],
                    "follow_up": ["Example follow-up question"],
                    "images": [{"url": "https://example.com/image.jpg", "description": "Example image"}],
                }
            ]
        }

def get_prompt(context, query) -> str:
    return f"""
    Based on the following query and context, provide a JSON object.

    QUERY: {query}

    CONTEXT: {context}

    Your response MUST be a valid JSON object with the following structure:
    {{
        "reason": "Your reasoning behind this answer, based solely on the information in the CONTEXT",
        "confidence_score": 0.95,
        "sources": [
            {{
                "title": "Source Title from CONTEXT",
                "url": "Source URL from CONTEXT",
                "content": "Relevant content from the source in CONTEXT",
                "score": 1.0
            }}
        ],
        "follow_up": ["A potential follow-up question", "Another potential follow-up question"],
        "images": [
            {{
                "url": "Image URL from Images in CONTEXT",
                "description": "Image description based on the CONTEXT"
            }}
        ]
    }}

    Guidelines:
    1. The confidence_score should be between 0.0 (not confident) and 1.0 (extremely confident).
    2. Include only relevant 2-3 sources from the provided CONTEXT.
    3. If images are relevant, include 3-4 of them from the 'images' field in the CONTEXT.
    4. Provide 2-3 follow-up questions as a list of strings.
    5. If you cannot find relevant information in the CONTEXT to answer the query, set the confidence_score to 0.0.

    Remember, your entire response must be a valid JSON object. Do not include any text outside of the JSON object.
    """

def _get_answer_prompt() -> str:
    return """
    You are a helpful search assistant named Mnemosyne.
    The system will provide you with a query and context from retrieved documents.
    You must answer the query using ONLY the information provided in the CONTEXT section below.
    Do not add any information that is not explicitly stated in the CONTEXT. 
    Your answer should be informed by the provided context. Your answer must be precise, of high-quality, and written by an expert using an unbiased and journalistic tone.

    INITIAL_QUERY: {query}

    CONTEXT:
    {context}

    Provide a detailed answer to the query using markdown format, based ONLY on information from the CONTEXT. Include code blocks from the CONTEXT using proper markdown formatting.
    """

def parse_llm_output(output: str) -> LLMOutput:
    try:
        parsed_output = json.loads(output)

        # Process sources to ensure they have a score
        processed_sources = []
        for source in parsed_output.get('sources', []):
            processed_sources.append(ResultInfo(**source))

        llm_output = LLMOutput(
            reason=parsed_output.get('reason', 'No reason provided'),
            confidence_score=float(parsed_output.get('confidence_score', 0.0)),
            sources=processed_sources,
            follow_up=parsed_output.get('follow_up', []),
            images=[ImageInfo(**image) for image in parsed_output.get('images', [])],
            timestamp=datetime.utcnow().isoformat()
        )

        return llm_output

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in LLM output: {e}")
    except Exception as e:
        raise ValueError(f"Error processing LLM output: {e}")