from service.MongoService import MongoService
from config import Config
import sys

def main():    
    mongo_service = MongoService(Config())
    # mongo_service.insert_data("https://akshaybahadur.medium.com/gymlytics-519caa05f045")
    mongo_service.retrieve_data("What is GymLytics?")


if __name__ == "__main__":
    main()