import os
from typing import List
from dataclasses import dataclass

from models import ProcessingEnum
from .BaseController import BaseController
from .ProjectController import ProjectController
from .PDFController import PDFController
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, PyMuPDFLoader



@dataclass
class Document:
    page_content: str
    metadata: dict


class ProcessController(BaseController):

    def __init__(self, project_id: str):
        super().__init__()

        self.project_id = project_id
        self.project_path = ProjectController().get_project_path(project_id=project_id)


    def get_file_extension(self, file_id: str):
        return os.path.splitext(file_id)[-1]
    

    def get_file_content(self, file_id: str):
        file_ext = self.get_file_extension(file_id=file_id)
        file_path = os.path.join(
            self.project_path,
            file_id)
        if not os.path.exists(file_path):
            return None

        # Extract Text file content
        if file_ext == ProcessingEnum.TXT.value:
            loader = TextLoader(file_path=file_path, encoding='utf-8')
            if not loader:
                return None
            return loader.load()
        
        # Extract PDF file content
        if file_ext == ProcessingEnum.PDF.value:
            loader = PDFController(project_id=self.project_id)
            if not loader:
                return None
            return loader.get_file_content(file_id=file_id) 

        return None
    

    def process_file_content(self, file_content: list, file_id: str,
                             chunk_size: int = 100, overlap_size: int = 20):
        
        # text_splitter = RecursiveCharacterTextSplitter(
        #     chunk_size=chunk_size,
        #     chunk_overlap=overlap_size,
        #     length_function=len,
        # )

        file_content_texts = [
            rec.page_content
            for rec in file_content
        ]

        file_content_metadata = [
            rec.metadata
            for rec in file_content
        ]

        # chunks = text_splitter.create_documents(
        #     file_content_texts,
        #     metadatas=file_content_metadata
        # )

        chunks = self.process_simpler_splitter(
            texts=file_content_texts,
            metadatas=file_content_metadata,
            chunk_size=chunk_size,
        )

        return chunks
    

    def process_simpler_splitter(
    self,
    texts: List[str],
    metadatas: List[dict],
    chunk_size: int,
    splitter_tag: str = "\n",
    ):
        chunks = []

        for text, metadata in zip(texts, metadatas):
            lines = [
                line.strip()
                for line in text.split(splitter_tag)
                if len(line.strip()) > 1
            ]

            cur_chunk = ""

            for line in lines:
                candidate = cur_chunk + line + splitter_tag

                if len(candidate) > chunk_size:
                    if cur_chunk.strip():
                        chunks.append(
                            Document(
                                page_content=cur_chunk.strip(),
                                metadata=metadata
                            )
                        )
                    cur_chunk = line + splitter_tag
                else:
                    cur_chunk = candidate

            if cur_chunk.strip():
                chunks.append(
                    Document(
                        page_content=cur_chunk.strip(),
                        metadata=metadata
                    )
                )

        return chunks



