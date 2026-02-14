from fastapi import Request
from models import ResponseSignal

class UploadRequestParser:

    @staticmethod
    async def parse(request: Request):
        content_type = request.headers.get("content-type", "")

        # JSON → URL
        if "application/json" in content_type:
            body = await request.json()
            return body.get("source"), body.get("url")

        # FORM → FILE
        if "multipart/form-data" in content_type:
            form = await request.form()
            source = form.get("source")
            if source:
                source = str(source)

            return source, None

        return None, None
