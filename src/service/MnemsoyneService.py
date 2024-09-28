from service.LLMService import LLMService
from service.MongoService import MongoService
from config import Config

class MnemsoyneService:
    def __init__(self, config: Config) -> None:
        self.llm_service = LLMService(config)
        self.mongo_service = MongoService(config)

    def insert_knowledge(self, url: str):
        self.mongo_service.insert_data(url)
        #TODO add more logic here

    def retrieve_knowlede(self, query: str):
        retrived_info = self.mongo_service.retrieve_data(query)
        knowledge_obj = self.llm_service.query_knowledge(retrived_info, query, model_name=Config.LLM.MODEL_NAME)
        return knowledge_obj