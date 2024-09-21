import MongoService

class LangchainService:
    def __init__(self, config):
        self.mongo_service = MongoService(config)
        

    def search(self, query):
        self.mongo_service.retrieve_data(query)
        #TODO add answering logic