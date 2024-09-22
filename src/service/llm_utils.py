
from pydantic.v1 import BaseModel, Field, validator

class KnowledgeObject:
    def __init__(self, query, answer) -> None:
        self.query = query
        self.follow_up_questions = None
        self.answer = answer
        self.results = []

def get_prompt(retrived_info, query) ->str:
    return ""

def parse_llm_response(query, new_parser, output, model_name, prompt, conversation_buf) -> KnowledgeObject:
    knowledge_obj = KnowledgeObject(query, output["answer"])
    # TODO Populate Knowledge Object
    return knowledge_obj

class LLMOutput(BaseModel):
    answer: str = Field(description="Answer to the query")
    citation: list = Field(description="List of URLs which are used to consolidate the knowledge")
    confidence_score: float = Field(description="The confidence score of the smart category")

    @validator('answer')
    def answer_validation(cls, field: str) -> str:
        if not field:
            raise ValueError("Answer is missing in the response")
        return field

    @validator('citation')
    def reason_validation(cls, field: list) -> list:
        if not field:
            raise ValueError("Citation is missing in the response")
        return field

    @validator('confidence_score')
    def confidence_score_validation(cls, field: float) -> float:
        if not field:
            raise ValueError("Confidence score is missing in the smart category")
        if type(field) is not float:
            raise ValueError("Confidence score should be a float")
        if field < 0 or field > 1:
            raise ValueError("Confidence score should be between 0 and 1")
        return round(field, 5)
