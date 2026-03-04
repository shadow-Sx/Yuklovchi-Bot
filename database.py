from pymongo import MongoClient
from config import MONGO_URI

client = MongoClient(MONGO_URI)
db = client["xanimelar_bot"]

contents = db["contents"]
required_channels = db["required_channels"]
optional_channels = db["optional_channels"]
admins = db["admins"]
