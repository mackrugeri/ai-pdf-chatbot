from app.schemas.common import APIModel


class CapabilitiesResponse(APIModel):
    ingestion_available: bool
    answers_available: bool
    max_upload_bytes: int
    max_selected_documents: int
