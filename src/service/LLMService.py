import logging

from langchain.callbacks import get_openai_callback
from langchain.chains import ConversationChain
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.output_parsers import OutputFixingParser, PydanticOutputParser
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_random_exponential
from llm_utils import *

from config import Config

logger = logging.getLogger()

class LLMService:

    def __init__(self, config: Config):
        self.client = OpenAI(api_key=config.OPENAI.API_KEY)

    @retry(wait=wait_random_exponential(min=0.1, max=0.5), stop=stop_after_attempt(2))
    def query_knowledge(self, retrived_info, query, model_name: str) -> str:
        prompt = get_prompt(retrived_info, query)
        gpt_model = ChatOpenAI(model_name=model_name, temperature=Config.LLM.TEMPERATURE, openai_api_key=self.secret,
                               request_timeout=Config.LLM.OPENAI_TIMEOUT)
        parser = PydanticOutputParser(pydantic_object=LLMOutput)
        conversation_buf = ConversationChain(
            llm=gpt_model,
            memory=ConversationBufferMemory()
        )
        with get_openai_callback() as cb:
            output = conversation_buf(
                prompt.format(
                    partial_variables={"format_instructions": parser.get_format_instructions()}
                )
            )
        new_parser = OutputFixingParser.from_llm(parser=parser, llm=gpt_model)
        knowledge_obj = parse_llm_response(query, new_parser, output, model_name, prompt, conversation_buf)
        logger.info(f"OpenAI response for query {query}", extra={
            "openai_cost": cb.total_cost,
            "openai_token_count": cb.total_tokens,
            "model_name": model_name,
            "knowledge_obj": str(knowledge_obj)
        })
        return knowledge_obj
