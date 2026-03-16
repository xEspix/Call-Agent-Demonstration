
from pymongo.mongo_client import MongoClient
import os
from dotenv import load_dotenv
load_dotenv()

MONGODB_URI=os.getenv("MONGODB_URI", "mongodb://localhost:27017/")

client=MongoClient(MONGODB_URI)

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)