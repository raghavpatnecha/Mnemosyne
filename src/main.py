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

def main():
    mongo_service = MongoService(Config())
    ms = MnemsoyneService(Config())
    # mongo_service.insert_data("https://akshaybahadur.medium.com/gymlytics-519caa05f045")
    # mongo_service.retrieve_data("Personalization?")
    for chunk in ms.retrieve_knowlede("What is gymlytics explain with add code"):
        #print(chunk)
        if chunk == "STREAM_START\n":
            # Start of answer stream
            pass
        elif chunk == "\nSTREAM_END\n":
            # End of answer stream, full JSON coming next
            pass
        elif chunk.startswith("{"):
            # This is the full JSON
            full_response = json.loads(chunk)
            print(full_response)
            # Process the full response
        else:
            # This is a chunk of the streamed answer
            print(chunk, end='|',flush=True)


if __name__ == "__main__":
    main()