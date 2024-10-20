import pymongo
from src.service.mongo_utils import *
from src.model.model_utls import *
import logging

logger = logging.getLogger()

class MongoService:
    def __init__(self, config):
        mongo_client = pymongo.MongoClient(f"mongodb://{config.MONGO.USERNAME}:{config.MONGO.PWRD}@cluster0-shard-00-00.8p0ks.mongodb.net:27017,cluster0-shard-00-01.8p0ks.mongodb.net:27017,cluster0-shard-00-02.8p0ks.mongodb.net:27017/?ssl=true&replicaSet=atlas-yxp1ty-shard-0&authSource=admin&retryWrites=true&w=majority")
        db = mongo_client[config.MONGO.DB_NAME]
        self.collection = db[config.MONGO.COLLECTION]
        self.dense_model = instantiate_model()

    def insert_data(self, url: str) -> None:
        md_dict = extract_data_from_firecrawl(url)
        chunks = divide_text_into_chunks(md_dict['content'])
        logger.info(f"Inserting for url: {url}, Number of chunks: {len(chunks)}")
        for i in range(len(chunks)):
            chunk = chunks[i]
            embeddings = self.dense_model.encode(chunk)
            md_dict['chunk'] = chunk
            md_dict['chunk_embedding'] = [embedding.tolist() for embedding in embeddings]
            md_dict['_id'] = f"{url}-{i}"  # Add the unique identifier
            self.collection.insert_one(md_dict)
            if i % 5 == 0:
                logger.info(f"inserting chunk index: {i} of {len(chunk)}")

    def retrieve_data(self, query: str) -> str:
        query_embedding = self.dense_model.encode(query).tolist()
        val = self.vector_search(index_name="vector_index", attr_name="chunk_embedding", embedding_vector=query_embedding)
        return val

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
                   "images":1,
                   "links":1,
                   "sourceURL":1,
                   "code_blocks":1,
                   "search_score": { "$meta": "vectorSearchScore" }
           }
           }
           ])
       return list(results)