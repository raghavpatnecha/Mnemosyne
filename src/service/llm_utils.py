from venv import logger
from pydantic.v1 import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime


class ImageInfo(BaseModel):
    url: str
    description: Optional[str] = None


class ResultInfo(BaseModel):
    title: str
    url: str
    content: str
    score: float


class KnowledgeObject(BaseModel):
    query: str
    answer: Optional[str] = None
    follow_up_questions: List[str] = []
    images: List[ImageInfo] = []
    results: List[ResultInfo] = []
    response_time: float


class LLMOutput(BaseModel):
    answer: str = Field(description="Answer to the query")
    reason: str = Field(description="The reason for this answer")
    confidence_score: float = Field(description="The confidence score of the answer")
    sources: Optional[List[ResultInfo]] = Field(default=None, description="Sources referenced for the answer")
    follow_up: List[str] = Field(default_factory=list, description="List of potential follow-up questions")
    images: Optional[List[ImageInfo]] = Field(default=None, description="Images related to the answer")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(),
                           description="Timestamp of when the response was generated")
    @validator('answer')
    def answer_validation(cls, field: str) -> str:
        if not field:
            raise ValueError("Answer is missing in the response")
        return field

    @validator('reason')
    def reason_validation(cls, field: str) -> str:
        if not field:
            raise ValueError("Reason is missing in the response")
        return field

    @validator('confidence_score')
    def confidence_score_validation(cls, field: float) -> float:
        if not isinstance(field, float):
            raise ValueError("Confidence score should be a float")
        if field < 0 or field > 1:
            raise ValueError("Confidence score should be between 0 and 1")
        return round(field, 5)

    @validator('sources', always=True)
    def sources_validation(cls, field: Optional[List[ResultInfo]]) -> Optional[List[ResultInfo]]:
        if field and not all(isinstance(source, ResultInfo) for source in field):
            raise ValueError("All sources should be ResultInfo objects")
        return field

    @validator('follow_up', always=True)
    def follow_up_validation(cls, field: List[str]) -> List[str]:
        if not isinstance(field, list):
            raise ValueError("Follow-up questions should be a list of strings")
        return field

def get_prompt(retrieved_info, query) -> str:
    return f"""
You are a helpful search assistant named Mnemosyne.
You must always return an answer in markdown format.
The system will provide you a query and context.
You must answer the query using ONLY the retrieved info list of dictionaries provided in the CONTEXT.
Do not add any information that is not explicitly stated in the CONTEXT. 
Your answer should be informed by the provided "Search results". Your answer must be precise, of high-quality, and written by an expert using an unbiased and journalistic tone.

INITIAL_QUERY: {query}

CONTEXT: {str(retrieved_info)}

Return a response in valid JSON OBJECT format with the following structure:
{{
    "answer": "A detailed answer to the query in markdown format, using ONLY information from the CONTEXT",
    "reason": "Your reasoning behind this answer, based solely on the information in the CONTEXT",
    "confidence_score": 0.95,
    "sources": [
        {{
            "title": "Source Title from CONTEXT",
            "url": "Source URL from CONTEXT",
            "content": "Relevant content from the source in CONTEXT",
            "score": 0.99
        }}
    ],
    "follow_up": ["A potential follow-up question", "Another potential follow-up question"],
    "images": [
        {{
            "url": "Image URL from CONTEXT",
            "description": "Image description from CONTEXT"
        }}
    ]
}}

Ensure that your answer is comprehensive and directly addresses the query, but ONLY use information provided in the CONTEXT.
Use markdown formatting for the answer, including appropriate headers, lists, and code blocks if necessary.
The confidence_score should be between 0.0 (not confident) and 1.0 (extremely confident).
Include only relevant sources and images from the provided CONTEXT.
Provide 2-3 follow-up questions as a list of strings.
"""


def parse_llm_response(query, parser, output, model_name, prompt_template, conversation_buf, retrieved_info):
    try:
        response_data = parser.parse(output["response"])
        #print(response_data)
        # Extracting data from response_data to fit the required structure

        formatted_response = KnowledgeObject(
            query=query,
            answer=response_data.answer,
            follow_up_questions=response_data.follow_up,
            images=response_data.images if response_data.images else [],
            results=response_data.sources if response_data.sources else [],
            response_time=0.0  # You'll need to calculate this based on your actual response time
        )

        return formatted_response.dict()

    except Exception as e:
        logger.error(f"Error parsing LLM response: {e}")
        return KnowledgeObject(
            query=query,
            answer=None,
            images=[],
            results=[],
            response_time=0.0
        ).dict()

