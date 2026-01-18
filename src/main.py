from fastapi import FastAPI
from routes import base, data, nlp
from contextlib import asynccontextmanager
from helpers.config import Settings, get_settings
from motor.motor_asyncio import AsyncIOMotorClient
from stores.llm.LLMProviderFactory import LLMProviderFactory
from stores.vectordb.VectorDBProviderFactory import VectorDBProviderFactory
from stores.llm.templates.template_parser import TemplateParser

@asynccontextmanager
async def lifespan(app: FastAPI):
    # -------- STARTUP --------
    settings: Settings = get_settings()

    app.mongo_conn = AsyncIOMotorClient(settings.MONGODB_URL)
    app.db_client = app.mongo_conn[settings.MONGODB_DATABASE]

    llm_provider_factory = LLMProviderFactory(settings)
    vectordb_provider_factory = VectorDBProviderFactory(settings)

    # generation client
    app.generation_client = llm_provider_factory.create(
        provider=settings.GENERATION_BACKEND
    )
    app.generation_client.set_generation_model(
        model_id=settings.GENERATION_MODEL_ID
    )

    app.template_parser = TemplateParser(
        language=settings.PRIMARY_LANG,
        default_language=settings.DEFAULT_LANG,
    )


    # embedding client
    app.embedding_client = llm_provider_factory.create(
        provider=settings.EMBEDDING_BACKEND
    )
    app.embedding_client.set_embedding_model(
        model_id=settings.EMBEDDING_MODEL_ID,
        embedding_size=settings.EMBEDDING_MODEL_SIZE,
    )

    app.vectordb_client = vectordb_provider_factory.create_provider(
        provider=settings.VECTOR_DB_BACKEND
    )
    app.vectordb_client.connect()

    yield  # 👈 application runs here

    # -------- SHUTDOWN --------
    app.mongo_conn.close()
    app.vectordb_client.disconnect()

app = FastAPI(lifespan=lifespan)

app.include_router(base.base_router)
app.include_router(data.data_router)
app.include_router(nlp.nlp_router)


