from pymongo import MongoClient
from config import MONGO_URI

client = MongoClient(MONGO_URI)
db = client["bot"]

users = db["users"]
required_channels = db["required_channels"]
optional_channels = db["optional_channels"]
referrals = db["referrals"]
settings = db["settings"]
broadcast = db["broadcast"]
