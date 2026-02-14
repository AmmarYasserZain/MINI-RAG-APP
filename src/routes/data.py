import os
import logging
import aiofiles
from models import ResponseSignal
from controllers import NLPController
from .schemes.data import ProcessRequest
from utils.request_parser import UploadRequestParser
from fastapi.responses import JSONResponse
from models.ChunkModel import ChunkModel
from models.AssetModel import AssetModel
from models.ProjectModel import ProjectModel
from models.enums.AssetTypeEnum import AssetTypeEnum
from models.db_schemes import Project, DataChunk, Asset
from helpers.config import Settings, get_settings
from controllers import DataController, ProjectController, ProcessController
from fastapi import File, APIRouter, UploadFile, status, Request, Depends, Body

logger = logging.getLogger("uvicorn.error")

data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"]
)


@data_router.post("/upload/{project_id}")
async def upload_data(request: Request, project_id: int, 
                    file: UploadFile | None = File(None),
                    app_settings: Settings = Depends(get_settings)):
    source, url = await UploadRequestParser.parse(request)

    if source is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": ResponseSignal.INVALID_SOURCE_TYPE.value}
        )
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)

    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
    data_controller = DataController()

    # For files
    if source == "file":

        if not file:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"signal": ResponseSignal.FILE_REQUIRED.value}
            )

        is_valid, result_signal = data_controller.validate_uploaded_file(file=file)
        if not is_valid:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"signal": result_signal}
            )

        file_hash = await data_controller.calculate_file_hash(
            file,
            app_settings.FILE_DEFAULT_CHUNK_SIZE
        )

        existing_asset = await asset_model.get_asset_by_hash(
            asset_project_id=project_id,
            file_hash=file_hash
        )

        if existing_asset:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "signal": ResponseSignal.FILE_ALREADY_EXISTS.value,
                    "file_id": str(existing_asset.asset_id),
                    "message": "This file has already been uploaded to this project"
                }
            )

        file_path, file_id = data_controller.generate_unique_filepath(
            file.filename,
            project_id=project_id
        )

        try:
            async with aiofiles.open(file_path, "wb") as f:
                while chunk := await file.read(app_settings.FILE_DEFAULT_CHUNK_SIZE):
                    await f.write(chunk)
        except Exception:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"signal": ResponseSignal.FILE_UPLOAD_FAILED.value}
            )

        asset_size = os.path.getsize(file_path)
        language = None

    # for Url Wekipedia
    elif source == "url":

        if not url:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"signal": ResponseSignal.INVALID_URL.value}
            )

        try:
            text, title = await data_controller.extract_wekepedia_text(url)
            language = data_controller.get_wikipedia_language(url)
        except ValueError:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"signal": ResponseSignal.WIKIPEDIA_PAGE_NOT_FOUND.value}
            )
        except Exception:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"signal": ResponseSignal.URL_EXTRACTION_FAILED.value}
            )

        file_hash = data_controller.calculate_text_hash(text)

        existing_asset = await asset_model.get_asset_by_hash(
            asset_project_id=project_id,
            file_hash=file_hash
        )

        if existing_asset:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "signal": ResponseSignal.FILE_ALREADY_EXISTS.value,
                    "file_id": str(existing_asset.asset_id),
                }
            )

        clean_name = data_controller.get_clean_file_name(title) + ".txt"

        file_path, file_id = data_controller.generate_unique_filepath(
            clean_name,
            project_id=project_id
        )

        try:
            await data_controller.save_text_file(text, file_path)
        except Exception:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"signal": ResponseSignal.TEXT_SAVE_FAILED.value}
            )

        asset_size = len(text.encode("utf-8"))

    else:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": ResponseSignal.INVALID_SOURCE_TYPE.value}
        )

    # Save to DB
    asset_resource = Asset(
        asset_project_id=project.project_id,
        asset_type=AssetTypeEnum.FILE.value,
        asset_name=file_id,
        asset_size=asset_size,
        asset_hash=file_hash,
    )

    asset_record = await asset_model.create_asset(asset=asset_resource)

    return JSONResponse(
        content={
            "signal": ResponseSignal.FILE_UPLOAD_SUCCESS.value,
            "file_id": str(asset_record.asset_id),
        }
    )

@data_router.post("/process/{project_id}")
async def process_endpoint(request: Request, project_id: int, process_request: ProcessRequest):

    chunk_size = process_request.chunk_size
    overlap_size = process_request.overlap_size
    do_reset = process_request.do_reset


    project_model = await ProjectModel.create_instance(
        db_client=request.app.db_client
    )

    project: Project = await project_model.get_project_or_create_one(project_id=project_id)

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
    )

    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)

    project_files_ids = {}
    if process_request.file_id:

        asset_record = await asset_model.get_asset_record(
            asset_project_id=project.project_id,
            asset_name=process_request.file_id
        )

        if asset_record is None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "signal": ResponseSignal.FILE_ID_ERROR.value,
                }
            )
        
        project_files_ids = {
            asset_record.asset_project_id: asset_record.asset_name
        }

    else:
        # Store the assets into the database
        asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
        project_files = await asset_model.get_all_project_assets(
            asset_project_id=project.project_id,
            asset_type=AssetTypeEnum.FILE.value,
        )

        project_files_ids = {
            record.asset_id: record.asset_name
            for record in project_files
        }
    
    if len(project_files_ids) == 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.NO_FILES_ERROR.value,
            }
        )

    process_controller = ProcessController(project_id=project_id)
    chunk_model = await ChunkModel.create_instance(
        db_client=request.app.db_client
    )

    if do_reset == 1:
        # delete associated vectors collection
        collection_name = nlp_controller.create_collection_name(project_id=project.project_id)
        _ = await request.app.vectordb_client.delete_collection(collection_name=collection_name)

        # delete associated chunks
        _ = await chunk_model.delete_chunks_by_project_id(
            project_id=project.project_id
        )
    
    no_records = 0
    no_files = 0

    for asset_id, file_id in project_files_ids.items():
        file_content = process_controller.get_file_content(file_id=file_id)

        if file_content is None:
            logger.error(f"Error while processing file: {file_id}")
            continue

        file_chunks = process_controller.process_file_content(
            file_content=file_content, 
            file_id=file_content,
            chunk_size=chunk_size,
            overlap_size=overlap_size
        )

        if file_chunks == None or len(file_chunks) == 0:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "signal": ResponseSignal.PROCESSING_FAILED.value
                }
            )

        file_chunks_records = [
            DataChunk(
                chunk_text=chunk.page_content,
                chunk_metadata=chunk.metadata,
                chunk_order=i+1,
                chunk_project_id=project.project_id,
                chunk_asset_id=asset_id
            )
            for i, chunk in enumerate(file_chunks)
        ]

            
        no_records += await chunk_model.insert_many_chunks(chunks=file_chunks_records)
        no_files += 1

    return JSONResponse(
        content={
            "signal": ResponseSignal.PROCESSING_SUCCESS.value,
            "inserted_chunks": no_records,
            "processed_files": no_files
        }
    )