import pymongo
from mongo.utils import *
from model.model_utls import *

class MongoService:
    def __init__(self, config):
        mongo_client = pymongo.MongoClient(f"mongodb://{config.MONGO.USERNAME}:{config.MONGO.PWRD}@cluster0-shard-00-00.8p0ks.mongodb.net:27017,cluster0-shard-00-01.8p0ks.mongodb.net:27017,cluster0-shard-00-02.8p0ks.mongodb.net:27017/?ssl=true&replicaSet=atlas-yxp1ty-shard-0&authSource=admin&retryWrites=true&w=majority")
        db = mongo_client[config.MONGO.DB_NAME]
        self.collection = db[config.MONGO.COLLECTION]
        self.dense_model = instantiate_model()

    def insert_data(self, url: str) -> None:
        title, article_content, images, code_blocks = extract_data_from_url(url)
        chunks = divide_text_into_chunks(article_content)
        for chunk in chunks:
            embeddings = self.dense_model.encode(chunk)
            article_data = {
                'title': title,
                'article_content': article_content,
                'chunk': chunk,
                'chunk_embedding': [embedding.tolist() for embedding in embeddings],
                'images': images,
                'code_blocks': code_blocks
            }
            self.collection.insert_one(article_data)

    def retrieve_data(self, query: str) -> str:
        query_embedding = self.dense_model.encode(query).tolist()
        val = self.vector_search(index_name="vector_index", attr_name="chunk_embedding", embedding_vector=query_embedding)
        print(val)

    def vector_search(self, index_name, attr_name, embedding_vector, limit=5):
       results = self.collection.aggregate([
           {
               '$vectorSearch': {
                   "index": index_name,
                   "path": attr_name,
                   "queryVector": embedding_vector,
                   "numCandidates": 10,
                   "limit": limit,
               }
           },
           ## We are extracting 'vectorSearchScore' here
           ## columns with 1 are included, columns with 0 are excluded
           {
               "$project": {
                   '_id' : 1,
                   'title' : 1,
                   "chunk":1,
                   "search_score": { "$meta": "vectorSearchScore" }
           }
           }
           ])
       return list(results)