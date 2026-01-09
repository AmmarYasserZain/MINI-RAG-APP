from fastapi import FastAPI
from routes import base, data
from contextlib import asynccontextmanager
from helpers.config import Settings, get_settings
from motor.motor_asyncio import AsyncIOMotorClient



@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = get_settings()
    
    # Startup Logic
    app.mongo_conn = AsyncIOMotorClient(settings.MONGODB_URL)
    app.db_client = app.mongo_conn[settings.MONGODB_DATABASE]

    yield  # The app runs while it stays here
    
    # Shutdown logic
    app.mongo_conn.close()


app = FastAPI(lifespan=lifespan)

app.include_router(base.base_router)
app.include_router(data.data_router)
