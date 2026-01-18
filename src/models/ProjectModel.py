import math
from .db_schemes import Project
from .BaseDataModel import BaseDataModel
from .enums.DataBaseEnum import DataBaseEnum
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection


class ProjectModel(BaseDataModel):
    def __init__(self, db_client: AsyncIOMotorDatabase):
        super().__init__(db_client=db_client)

        self.collection: AsyncIOMotorCollection = self.db_client[DataBaseEnum.COLLECTION_PROJECT_NAME.value]

    @classmethod
    async def create_instance(cls, db_client: AsyncIOMotorDatabase):
        instance = cls(db_client)
        await instance.init_collections()
        return instance

    async def init_collections(self):
        all_collections = await self.db_client.list_collection_names()
        if DataBaseEnum.COLLECTION_PROJECT_NAME.value not in all_collections:
            self.collection = self.db_client[DataBaseEnum.COLLECTION_PROJECT_NAME.value]
            indexes = Project.get_indexes()
            for index in indexes:
                await self.collection.create_index(
                    index["key"],
                    name=index["name"],
                    unique=index["unique"]
                )

    async def create_project(self, project: Project) -> Project:

        result = await self.collection.insert_one(project.model_dump(by_alias=True, exclude_unset=True))
        project.id = result.inserted_id

        return project
    
    async def get_project_or_create_one(self, project_id: str) -> Project:

        record = await self.collection.find_one(
            {
                "project_id" : project_id
            }
        )

        if record is None:
            # Create a new project
            project = Project(project_id=project_id)
            project = await self.create_project(project=project)

            return project
        else:
            return Project(**record)
        
    
    async def get_all_projects(self, page: int=1, page_size: int=10):
        # count total number of pages
        total_documents = await self.collection.count_documents({})

        # calculate the total number of pages
        total_pages = int(math.ceil(total_documents / page_size))

        cursor = self.collection.find().skip( (page - 1) * page_size ).limit(page_size)
        projects = []

        async for doc in cursor:
            projects.append(
                Project(**doc)
            )

        return projects, total_pages
