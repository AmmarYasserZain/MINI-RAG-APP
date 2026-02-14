import hashlib
import os
import re
from fastapi import UploadFile
from models import ResponseSignal
from .BaseController import BaseController
from .ProjectController import ProjectController
import wikipediaapi
import aiofiles
from urllib.parse import urlparse, unquote

class DataController(BaseController):
    def __init__(self):
        super().__init__()
        self.size_scale = 1024 * 1024 # convert MB to bytes
    
    async def calculate_file_hash(self, file: UploadFile, chunk_size: int= 8192) -> str:
        sha256_hash = hashlib.sha256()
        await file.seek(0)

        # Read file in chunks and update hash
        while chunk := await file.read(chunk_size):
            sha256_hash.update(chunk)

        await file.seek(0)

        return sha256_hash.hexdigest()

    def validate_uploaded_file(self, file: UploadFile):

        if file.content_type not in self.app_settings.FILE_ALLOWED_TYPES:
            return False, ResponseSignal.FILE_TYPE_NOT_SUPPORTED.value
        
        if file.size > self.app_settings.FILE_MAX_SIZE * self.size_scale:
            return False, ResponseSignal.FILE_SIZE_EXCEEDED.value
        
        return True, ResponseSignal.FILE_VALIDATED_SUCCESS.value
    

    def generate_unique_filepath(self, orig_file_name: str, project_id: str):

        random_key = self.generate_random_string()
        project_path = ProjectController().get_project_path(project_id=project_id)

        cleaned_file_name = self.get_clean_file_name(orig_file_name=orig_file_name)
        new_file_path = os.path.join(
            project_path,
            random_key + '_' + cleaned_file_name
        )

        while os.path.exists(new_file_path):
            random_key = self.generate_random_string()
            new_file_path = os.path.join(
                project_path,
                random_key + '_' + cleaned_file_name
            )

        return new_file_path, random_key + '_' + cleaned_file_name



    def get_clean_file_name(self, orig_file_name: str):

        # remove any special characters, except underscore and .
        cleaned_file_name = re.sub(r'[^\w.]', '', orig_file_name.strip())

        # replace spaces with underscore
        cleaned_file_name = cleaned_file_name.replace(" ", "_")

        return cleaned_file_name

    def get_wikipedia_title(self, url: str) -> str:
        parsed = urlparse(url)

        if "/wiki/" not in parsed.path:
            raise ValueError("Not a wikipedia article url")

        title = parsed.path.split("/wiki/")[-1]
        return unquote(title)

    def get_wikipedia_language(self, url: str) -> str:
        parsed = urlparse(url)
        host = parsed.netloc.split(".")[0]   # en or ar
    
        if host not in ["en", "ar"]:
            raise ValueError("Unsupported wikipedia language")
    
        return host

    async def extract_wekepedia_text(self, url: str) -> tuple[str, str]:
        title = self.get_wikipedia_title(url)
        language = self.get_wikipedia_language(url)

        wiki = wikipediaapi.Wikipedia(
            language=language,
            extract_format=wikipediaapi.ExtractFormat.WIKI,
            user_agent="dataset-builder/1.0"
        )

        page = wiki.page(title)

        if not page.exists():
            raise ValueError("Wikipedia page not found")

        return page.text, page.title
    def calculate_text_hash(self, text: str) -> str:
        sha256_hash = hashlib.sha256()
        sha256_hash.update(text.encode("utf-8"))
        return sha256_hash.hexdigest()
    
    async def save_text_file(self, text: str, file_path: str):
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(text)
