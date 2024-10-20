import json

from flask import jsonify

from service.MongoService import MongoService
from service.MnemsoyneService import MnemsoyneService
from config import Config
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).absolute().parents[2].absolute()
sys.path.insert(0, str(PROJECT_ROOT))
#print(PROJECT_ROOT)
#from gpt4free.g4f.client import Client

async def main_llm():
    mongo_service = MongoService(Config())
    ms = MnemsoyneService(Config())
    # mongo_service.insert_data("https://akshaybahadur.medium.com/gymlytics-519caa05f045")
    # mongo_service.retrieve_data("Personalization?")
    knowledge_obj_generator = await ms.retrieve_knowlede("Who is Akshay Bahadur, explain his life at CMU")

    async for chunk in knowledge_obj_generator:
        print(chunk)
        if isinstance(chunk, dict):
            yield f'data: {json.dumps(chunk)}\n\n'
        else:
            yield f'data: {chunk}\n\n'


if __name__ == "__main__":
    main_llm()