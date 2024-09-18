from mongo.MongoService import MongoService
from config import Config

def main():    
    mongo_service = MongoService(Config())
    mongo_service.retrieve_data("What is Personalization?")


if __name__ == "__main__":
    main()