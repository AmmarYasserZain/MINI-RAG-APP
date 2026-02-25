import os
from typing import List
from dataclasses import dataclass
from helpers.config import get_settings, Settings

from models import ProcessingEnum
from .BaseController import BaseController
from .ProjectController import ProjectController
from stores.llm import GeminiProvider

import base64
from glob import glob
from pdf2image import convert_from_path
from PIL import Image
from PIL import ImageEnhance


@dataclass
class Document:
    page_content: str
    metadata: dict

class PDFController(BaseController):
    def __init__(self, project_id: str):
        super().__init__()

        settings: Settings = get_settings()

        self.project_id = project_id
        self.project_path = ProjectController().get_project_path(project_id=project_id)

        # OCR Model
        self.ocr_client = GeminiProvider(
            api_key=settings.GEMINI_API_KEY,
        )

        self.ocr_client.set_ocr_model(
            model_id=settings.OCR_MODEL_ID
        )

    

    def get_file_content(self, file_id: str) -> List[Document]:
        
        file_path = os.path.join(
            self.project_path,
            file_id
        )

        if not os.path.exists(file_path):
            return None
        
        file_content = self.ocr_client.get_pdf_content(
            pdf_path=file_path
        )

        file_content = [
            Document(
                page_content=rec,
                metadata={}
            )
            for rec in file_content
        ]

        return file_content
        

