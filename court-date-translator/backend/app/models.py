"""
Pydantic models for the API requests and responses.
"""

from typing import List, Optional

from pydantic import BaseModel


class UploadResponse(BaseModel):
    """Response returned after a file upload + text extraction."""

    filename: str
    text_preview: str
    status: str


class AnalysisResult(BaseModel):
    """Structured output produced by the LLM for a legal document."""

    document_type: Optional[str] = None
    court_authority: Optional[str] = None
    parties: List[str] = []
    case_number: Optional[str] = None
    court_date: Optional[str] = None
    deadlines: List[str] = []
    required_actions: List[str] = []
    simplified_explanation_en: Optional[str] = None
    simplified_explanation_hi: Optional[str] = None
    warnings: List[str] = []
    action_steps: List[str] = []


class UploadAnalysisResponse(BaseModel):
    """Full response combining upload metadata + analysis."""

    document_id: int
    filename: str
    text_preview: str
    status: str
    result: AnalysisResult


# --- Authentication ---


class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


# --- Chatbot ---


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    reply_id: int


class DocumentListResponse(BaseModel):
    documents: list


class DocumentResponse(BaseModel):
    document: dict


class ChatHistoryResponse(BaseModel):
    messages: list


# --- Folders ---


class FolderCreateRequest(BaseModel):
    name: str


class FolderRenameRequest(BaseModel):
    name: str


class MoveDocumentRequest(BaseModel):
    folder_id: Optional[int] = None
