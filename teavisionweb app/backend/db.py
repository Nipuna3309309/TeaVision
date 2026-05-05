"""
MongoDB connection using Motor (async driver)
"""
import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://it22154576:200102400102@nipuna.swzwnwc.mongodb.net/carserve")

client = AsyncIOMotorClient(MONGODB_URI)
db = client.carserve
