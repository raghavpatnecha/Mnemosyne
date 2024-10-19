import json
import time
from datetime import datetime
from langchain.chains.conversation.base import ConversationChain
from langchain.chains.llm import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain_community.callbacks import get_openai_callback
from langchain_community.chat_models import ChatOllama, ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.callbacks import StreamingStdOutCallbackHandler, CallbackManager, BaseCallbackHandler
from src.service.llm_utils import *

from src.config import Config
import logging
from typing import List, Dict, Generator
from tenacity import retry, wait_random_exponential, stop_after_attempt
from concurrent.futures import ThreadPoolExecutor, Future
logger = logging.getLogger(__name__)
logging.basicConfig()
logger.setLevel(logging.INFO)


class StreamingCallback(BaseCallbackHandler):
    def __init__(self):
        self.text = ""

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.text += token
        yield f"data: {token}\n\n"

class LLMService:
    def __init__(self, config: Config):
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.config = config

    @retry(wait=wait_random_exponential(min=0.1, max=0.5), stop=stop_after_attempt(5), reraise=True)
    def query_knowledge(self, retrieved_info: List[Dict], query: str, model_name: str) -> Generator[str, None, None]:
        context = json.dumps(retrieved_info, indent=2)
        #context = retrieved_info

        # First, stream the answer
        answer_stream = self._stream_answer(query, context, model_name)
        # Use a Future to store the streamed answer

        streamed_answer_future = Future()

        # Yield from _combine_streams, which will set the result of streamed_answer_future
        yield from self._combine_streams(answer_stream, streamed_answer_future)
        # Now that we have the full streamed answer, generate the full JSON
        json_future = self.executor.submit(self._generate_full_json, query, context, model_name,
                                           streamed_answer_future.result())
        # Yield the full JSON
        # yield json.dumps(json_future.result())
        yield json_future.result()


    def _stream_answer(self, query: str, context: str, model_name: str) -> Generator[str, None, None]:
        prompt_template = PromptTemplate(template=get_answer_prompt(),input_variables=["query", "context"])
        callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
        if "gpt" in model_name:
            gpt_model = ChatOpenAI(model_name=model_name, temperature=Config.LLM.TEMPERATURE, openai_api_key=self.config.OPENAI.API_KEY,
                               request_timeout=Config.LLM.OPENAI_TIMEOUT)
        else:
            gpt_model = ChatOllama(model=model_name, temperature=self.config.LLM.TEMPERATURE, callbacks=callback_manager)
        llm_chain = LLMChain(llm=gpt_model, prompt=prompt_template)
        return llm_chain.stream({"query": query, "context": context})


    def _generate_full_json(self, query: str, context: str, model_name: str,streamed_answer: str) -> dict:
        prompt = get_prompt(context, query)
        if "gpt" in model_name:
            gpt_model = ChatOpenAI(model_name=model_name, temperature=Config.LLM.TEMPERATURE, openai_api_key=self.config.OPENAI.API_KEY,
                               request_timeout=Config.LLM.OPENAI_TIMEOUT)
        else:
            gpt_model = ChatOllama(model=model_name, temperature=self.config.LLM.TEMPERATURE,
                                request_timeout=self.config.LLM.OPENAI_TIMEOUT)

        conversation_buf = ConversationChain(llm=gpt_model, memory=ConversationBufferMemory())
        with get_openai_callback() as cb:
            output = conversation_buf.invoke(prompt)
        try:
            llm_output = parse_llm_output(output['response'])
            structured_dict = llm_output.dict()
            structured_dict['response_time'] = cb.total_tokens
            logger.info(f"OpenAI response for query {query}", extra={
                "openai_cost": cb.total_cost,
                "openai_token_count": cb.total_tokens,
                "model_name": model_name,
                "knowledge_obj": json.dumps(structured_dict)
            })
            return structured_dict

        except ValueError as e:
            logger.error(f"Error processing LLM response: {str(e)}")
            default_response = LLMOutput(
                reason="Failed to parse the response",
                confidence_score=0.0,
                sources=[],
                follow_up=[],
                images=[],
                timestamp=datetime.utcnow().isoformat()
            )
            default_dict = default_response.dict()
            default_dict['response_time'] = cb.total_tokens
            return default_dict

    def _combine_streams(self, answer_stream: Generator[Dict, None, None], streamed_answer_future: Future) -> Generator[
        str, None, None]:
        streamed_answer = ""
        for chunk in answer_stream:
            if 'text' in chunk:
                content = chunk['text']
                if content:
                    streamed_answer += content
                    yield content
        streamed_answer_future.set_result(streamed_answer)

