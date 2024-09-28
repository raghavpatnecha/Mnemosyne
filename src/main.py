from service.MongoService import MongoService
from service.MnemsoyneService import MnemsoyneService
from config import Config
import sys

def main():    
    mongo_service = MongoService(Config())
    ms = MnemsoyneService(Config())
    # mongo_service.insert_data("https://akshaybahadur.medium.com/gymlytics-519caa05f045")
    # mongo_service.retrieve_data("Personalization?")
    ms.retrieve_knowlede("Personalization")


if __name__ == "__main__":
    main()