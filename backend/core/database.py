"""MongoDB async database connection - single source of truth"""
from motor.motor_asyncio import AsyncIOMotorClient
from core.config import MONGO_URL, DB_NAME

client: AsyncIOMotorClient = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
