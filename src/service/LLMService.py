import logging
import json
from langchain.chains.conversation.base import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.output_parsers import OutputFixingParser
from langchain_community.callbacks import get_openai_callback
from langchain_community.chat_models import ChatOllama
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from tenacity import retry, stop_after_attempt, wait_random_exponential
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).absolute().parents[1].absolute()
sys.path.insert(0, str(PROJECT_ROOT))
from config import Config
from service.llm_utils import parse_llm_response, LLMOutput, KnowledgeObject, get_prompt, ImageInfo, ResultInfo

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class LLMService:
    def __init__(self, config: Config):
        self.config = config

    @retry(wait=wait_random_exponential(min=0.1, max=0.5), stop=stop_after_attempt(5), reraise=True)
    def query_knowledge(self, retrieved_info: str, query: str, model_name: str) -> dict:
        prompt = get_prompt(retrieved_info, query)

        gpt_model = ChatOllama(model=model_name, temperature=self.config.LLM.TEMPERATURE,
                               request_timeout=self.config.LLM.OPENAI_TIMEOUT)
        parser = PydanticOutputParser(pydantic_object=LLMOutput)

        prompt_template = PromptTemplate(
            template=prompt,
            input_variables=[]
        )

        conversation_buf = ConversationChain(
            llm=gpt_model,
            memory=ConversationBufferMemory()
        )

        with get_openai_callback() as cb:
            output = conversation_buf.invoke(prompt)
        print(output)
        new_parser = OutputFixingParser.from_llm(parser=parser, llm=gpt_model)
        structured_output = parse_llm_response(query, new_parser, output, model_name, prompt_template, conversation_buf,
                                               retrieved_info)

        # Add response time to the structured output
        structured_output['response_time'] = cb.total_tokens

        logger.info(f"OpenAI response for query {query}", extra={
            "openai_cost": cb.total_cost,
            "openai_token_count": cb.total_tokens,
            "model_name": model_name,
            "knowledge_obj": json.dumps(structured_output)
        })
        #print(structured_output)
        return structured_output