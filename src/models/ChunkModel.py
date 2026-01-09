from typing import List
from bson import ObjectId
from pymongo import InsertOne
from .db_schemes import DataChunk
from .BaseDataModel import BaseDataModel
from .enums.DataBaseEnum import DataBaseEnum



class ChunkModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.collection = self.db_client[DataBaseEnum.COLLECTION_CHUNK_NAME.value]

    
    async def create_chunk(self, chunk: DataChunk) -> DataChunk:

        result = await self.collection.insert_one(chunk.model_dump(by_alias=True, exclude_unset=True))
        chunk._id = result.inserted_id

        return chunk
    
    async def get_chunk(self, chunk_id: str) -> DataChunk:
        result = await self.collection.find_one({
            "_id" : ObjectId(chunk_id) 
        })

        if result is None:
            return None

        return DataChunk(**result)
    

    async def insert_many_chunks(self, chunks: List[DataChunk], batch_size: int=100):

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]

            operations = [
                InsertOne(chunk.model_dump())
                for chunk in batch
            ]

            await self.collection.bulk_write(operations)

        return len(chunks)
    

    async def delete_chunks_by_project_id(self, project_id: ObjectId):
        result = await self.collection.delete_many({
            "chunk_project_id": project_id
        })

        return result.deleted_count
    




