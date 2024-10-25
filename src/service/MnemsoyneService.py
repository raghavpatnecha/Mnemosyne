from joblib import executor

from src.service.LLMService import LLMService,LLMMode
from src.service.MongoService import MongoService
from src.config import Config

class MnemsoyneService:
    def __init__(self, config: Config) -> None:
        self.llm_service = LLMService(config)
        self.mongo_service = MongoService(config)

    def insert_knowledge(self, url: str):
        self.mongo_service.insert_data(url)
        #TODO add more logic here

    def retrieve_knowlede(self, query: str, llm_mode: LLMMode):
        retrived_info = self.mongo_service.retrieve_data(query)
        knowledge_obj = self.llm_service.query_knowledge(retrived_info, query, model_name=Config.LLM.MODEL_NAME,
                                                         mode=llm_mode)
        return knowledge_obj