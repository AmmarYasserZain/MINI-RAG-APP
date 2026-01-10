from helpers.config import Settings, get_settings
from motor.motor_asyncio import AsyncIOMotorDatabase


class BaseDataModel:
    def __init__(self, db_client: AsyncIOMotorDatabase):
        self.db_client: AsyncIOMotorDatabase = db_client
        self.app_settings: Settings = get_settings()




