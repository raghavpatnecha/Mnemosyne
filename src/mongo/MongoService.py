import pymongo
from config import Config
from utils import *

class MangoService:
    def __init__(self) -> None:
        mongo_client = pymongo.MongoClient(f"mongodb://{Config.MONGO.USERNAME}:{Config.MONGO.PWRD}@cluster0-shard-00-00.8p0ks.mongodb.net:27017,cluster0-shard-00-01.8p0ks.mongodb.net:27017,cluster0-shard-00-02.8p0ks.mongodb.net:27017/?ssl=true&replicaSet=atlas-yxp1ty-shard-0&authSource=admin&retryWrites=true&w=majority")
        db = mongo_client[" Mnemosyne"]
        self.collection = db['medium']

    def insert_data(self, url: str) -> None:
        title, article_content, images, code_blocks = extract_data_from_url(url)

    def retrieve_data(self, query: str) -> str:
        pass