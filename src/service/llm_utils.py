
from pydantic.v1 import BaseModel, Field, validator

class KnowledgeObject:
    def __init__(self) -> None:
        self.query = ""
        self.follow_up_questions = ""
        self.answer = ""
        self.results = []

def get_prompt(retrived_info, query) ->str:
    return  f"""
You are a helpful search assistant named - Mnemsoyne.
You must always return an answer in markdown format.
The system will provide you a query and context.
You must answer the query using the retrieved info list of dictionaries
Return a response in valid JSON string format with the query answer in markdown as `answer`, your `reason` behind this choice and `confidence_score` as a metric expressing how certain you are of your answer
          (this must be between 0.0, not confident, to 1.0, extremely confident)

### Initial Query : {query}

### Context : {str(retrived_info)}

"""

def parse_llm_response(query, new_parser, output, model_name, prompt, conversation_buf, retrived_info) -> KnowledgeObject:
    knowledge_obj = KnowledgeObject()
    knowledge_obj.query = query
    knowledge_obj.answer = output["answer"]
    knowledge_obj.results = retrived_info
    return knowledge_obj

class LLMOutput(BaseModel):
    answer: str = Field(description="Answer to the query")
    reason: str = Field(description="The reason for this answer")
    confidence_score: float = Field(description="The confidence score of the answer")

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
        if not field:
            raise ValueError("Confidence score is missing in the smart category")
        if type(field) is not float:
            raise ValueError("Confidence score should be a float")
        if field < 0 or field > 1:
            raise ValueError("Confidence score should be between 0 and 1")
        return round(field, 5)
