import json
import logging
import json_repair
from typing import List, Optional

from google import genai
from google.genai.types import Part, Content, Blob, GenerateContentConfig, ThinkingConfig, ThinkingLevel

class GeminiProvider():

    def __init__(self, api_key: str,
                       default_generation_max_output_tokens: int=8000,
                       default_generation_temperature: float=0.1):
        

        self.api_key = api_key
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature

        self.ocr_model_id = None

        self.client = genai.Client(
            api_key = api_key,
            http_options={'api_version': 'v1alpha'}
        )

        self.logger = logging.getLogger(__name__)


    def set_ocr_model(self, model_id: str):
        self.ocr_model_id = model_id
        

    def read_pdf(self, pdf_path: str) -> bytes | None:
        try:
            with open(pdf_path, "rb") as f:
                return f.read()
        except FileNotFoundError:
            self.logger.error(
                f"Gemini OCR: pdf file not found at path='{pdf_path}'"
            )
            return None
    

    def build_ocr_message(self, pdf_path: str) -> Content | None:

        prompt = """
            You are a professional OCR Details Extractor.

            Your task is to extract all text content from the given PDF file and convert it into a clean JSON format.
            Follow these rules strictly:

            1. Extract the **full text content** from the entire PDF file exactly as it appears.
            2. Preserve the natural reading order of the text (page by page).
            3. Structure the JSON output like this:

            {
            "content": "<full text content of the PDF here>"
            }

            4. Do **not** add any introduction, explanation, or extra text.
            5. Do **not** include markdown, comments, or formatting—only plain text inside the "content" field.
            6. Ensure the output is valid JSON.

            Return **only** the JSON.
        """.strip()


        pdf_bytes = self.read_pdf(pdf_path)
        if not pdf_bytes or len(pdf_bytes) == 0:
            self.logger.error("Gemini OCR aborted: pdf_bytes is empty or failed to load")
            return None
        
        content = Content(
            parts=[
                Part(text=prompt),
                Part(
                    inline_data=Blob(
                        mime_type="application/pdf",
                        data=pdf_bytes
                    )
                )
            ]
        )

        return content


    @staticmethod
    def parse_json(text: str) -> Optional[dict]:
        try:
            return json_repair.loads(text)
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to parse JSON: {e}")
            return None
        

    def generate_ocr_content(self, pdf_path: str, 
                             max_output_tokens: int = None, 
                             temperature: float = None):
        if not self.client:
            self.logger.error("Gemini client was not set")
            return None

        if not self.ocr_model_id:
            self.logger.error("OCR model for Gemini was not set")
            return None

        ocr_message = self.build_ocr_message(pdf_path=pdf_path)
        if not ocr_message:
            return None
        
        max_output_tokens = max_output_tokens if max_output_tokens else self.default_generation_max_output_tokens
        temperature = temperature if temperature else self.default_generation_temperature

        # Send request to Gemini OCR model
        response = self.client.models.generate_content(
            model=self.ocr_model_id,
            contents=[ocr_message],
            config=GenerateContentConfig(
                thinking_config=ThinkingConfig(
                    thinking_level=ThinkingLevel.LOW
                ),
                temperature=0.2,
                top_p=0.1,
                top_k=1,
            )
        )

        return response
    

    def get_pdf_content(self, pdf_path: str, 
                      max_output_tokens: int = None, 
                      temperature: float = None) -> List[str]:
    
        response = self.generate_ocr_content(
            pdf_path=pdf_path,
            max_output_tokens=max_output_tokens,
            temperature=temperature
        )

        if not response or not getattr(response, "candidates", None):
            self.logger.error("Gemini OCR returned no candidates")
            return []

        raw_text = response.candidates[0].content.parts[0].text
        cleaned_text = raw_text.replace("```json", "").replace("```", "").strip()

        parsed = self.parse_json(cleaned_text)
        if not parsed or "content" not in parsed:
            return []

        content = parsed.get("content", "")
        content = [line.strip() for line in content.split("\n") if line.strip()]

        return content
