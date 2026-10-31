"""
FastAPI application entrypoint and HTTP endpoints.

Feature set:
- User registration / login (JWT auth)
- PDF upload + LLM analysis, persisted per-user in SQLite
- User-created folders to organize documents
- "My Documents" listing + per-document detail
- A per-document AI chatbot assistant (Gemini / OpenAI / Ollama)
"""

import json
import logging
from typing import List

import jwt as pyjwt
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from . import database
from .config import settings
from .database import ChatMessage, Document, Folder, User, create_all, get_db
from .llm_processor import analyze_legal_document, chat_about_document
from .models import (
    AnalysisResult,
    AuthResponse,
    ChatRequest,
    ChatResponse,
    FolderCreateRequest,
    FolderRenameRequest,
    LoginRequest,
    MoveDocumentRequest,
    RegisterRequest,
    UploadAnalysisResponse,
)
from .pdf_parser import extract_text_from_pdf
from .security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables on startup.
create_all()

app = FastAPI(
    title="Court Date & Legal Notice Translator",
    description="Upload a legal notice PDF, get a clear action-oriented "
    "summary, and chat with an AI assistant about the document.",
    version="2.0.0",
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

bearer_scheme = HTTPBearer(auto_error=False)


# --- Auth dependency -----------------------------------------------------
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the Bearer token."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (pyjwt.ExpiredSignatureError, pyjwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# --- Health --------------------------------------------------------------
@app.get("/ping")
def ping():
    """Health check endpoint."""
    return {"status": "ok"}


# --- Auth ----------------------------------------------------------------
@app.post("/auth/register", response_model=AuthResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Create a new user account and return a token."""
    email = req.email.strip().lower()
    if not req.full_name.strip() or not email or not req.password:
        raise HTTPException(status_code=400, detail="All fields are required")
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Please provide a valid email")

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user = User(
        full_name=req.full_name.strip(),
        email=email,
        hashed_password=hash_password(req.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.email)
    return AuthResponse(
        access_token=token,
        user={"id": user.id, "full_name": user.full_name, "email": user.email},
    )


@app.post("/auth/login", response_model=AuthResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate a user and return a token."""
    user = db.query(User).filter(User.email == req.email.strip().lower()).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.id, user.email)
    return AuthResponse(
        access_token=token,
        user={"id": user.id, "full_name": user.full_name, "email": user.email},
    )


@app.get("/auth/me")
def me(user: User = Depends(get_current_user)):
    """Return the currently authenticated user's info."""
    return {"id": user.id, "full_name": user.full_name, "email": user.email}


# --- Upload + analysis ---------------------------------------------------
@app.post("/upload", response_model=UploadAnalysisResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    language: str = "hindi",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Authenticated PDF upload: extract text, analyze with the LLM, and persist
    the document + analysis for the current user.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported. Please upload a .pdf document.",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    if len(file_bytes) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {settings.MAX_FILE_SIZE // (1024 * 1024)} MB.",
        )

    try:
        text = extract_text_from_pdf(file_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    text_preview = text[:500] + ("..." if len(text) > 500 else "")

    try:
        raw_analysis = analyze_legal_document(text, target_language=language)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    result = AnalysisResult(**raw_analysis)

    # Persist the document + analysis for this user.
    doc = Document(
        user_id=user.id,
        filename=file.filename,
        text_preview=text_preview,
        language=language,
        analysis=json.dumps(raw_analysis, ensure_ascii=False),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return UploadAnalysisResponse(
        document_id=doc.id,
        filename=file.filename,
        text_preview=text_preview,
        status="success",
        result=result,
    )


# --- Documents -----------------------------------------------------------
@app.get("/documents")
def list_documents(
    folder_id: int = None,
    unfiled: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List the current user's saved documents (newest first).

    Optional filters (mutually exclusive):
    - ``folder_id`` : only documents inside the given folder
    - ``unfiled``   : only documents not inside any folder
    """
    query = db.query(Document).filter(Document.user_id == user.id)
    if folder_id is not None:
        query = query.filter(Document.folder_id == folder_id)
    elif unfiled:
        query = query.filter(Document.folder_id.is_(None))
    docs = query.order_by(desc(Document.created_at)).all()
    return {"documents": [d.to_dict() for d in docs]}


def _get_owned_document(doc_id: int, user: User, db: Session) -> Document:
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc or doc.user_id != user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


def _get_owned_folder(folder_id: int, user: User, db: Session) -> "Folder":
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder or folder.user_id != user.id:
        raise HTTPException(status_code=404, detail="Folder not found")
    return folder


# --- Folders -----------------------------------------------------------
@app.get("/folders")
def list_folders(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the current user's folders, each with its document count."""
    folders = (
        db.query(Folder)
        .filter(Folder.user_id == user.id)
        .order_by(Folder.name.asc())
        .all()
    )
    counts = (
        db.query(Document.folder_id, func.count(Document.id))
        .filter(Document.user_id == user.id, Document.folder_id.isnot(None))
        .group_by(Document.folder_id)
        .all()
    )
    count_map = {fid: count for fid, count in counts}
    return {"folders": [f.to_dict(count_map.get(f.id, 0)) for f in folders]}


@app.post("/folders")
def create_folder(
    req: FolderCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new folder for the current user."""
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Folder name cannot be empty")
    if len(name) > 60:
        raise HTTPException(status_code=400, detail="Folder name is too long (max 60 chars)")

    folder = Folder(user_id=user.id, name=name)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return {"folder": folder.to_dict(document_count=0)}


@app.patch("/folders/{folder_id}")
def rename_folder(
    folder_id: int,
    req: FolderRenameRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rename one of the current user's folders."""
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Folder name cannot be empty")
    folder = _get_owned_folder(folder_id, user, db)
    folder.name = name
    db.commit()
    db.refresh(folder)
    count = db.query(Document).filter(Document.folder_id == folder.id).count()
    return {"folder": folder.to_dict(document_count=count)}


@app.delete("/folders/{folder_id}")
def delete_folder(
    folder_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a folder. Documents inside it are NOT deleted; they become
    "unfiled" instead.
    """
    folder = _get_owned_folder(folder_id, user, db)
    db.query(Document).filter(Document.folder_id == folder.id).update(
        {Document.folder_id: None}
    )
    db.delete(folder)
    db.commit()
    return {"status": "deleted"}


@app.put("/documents/{doc_id}/folder")
def move_document(
    doc_id: int,
    req: MoveDocumentRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Move a document into a folder (or unfiled when folder_id is null)."""
    doc = _get_owned_document(doc_id, user, db)
    if req.folder_id is not None:
        _get_owned_folder(req.folder_id, user, db)
    doc.folder_id = req.folder_id
    db.commit()
    db.refresh(doc)
    return {"document": doc.to_dict()}


@app.get("/documents/{doc_id}")
def get_document(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch a single document including its full analysis."""
    doc = _get_owned_document(doc_id, user, db)
    return {"document": doc.to_dict(include_analysis=True)}


@app.delete("/documents/{doc_id}")
def delete_document(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete one of the current user's documents and its chat history."""
    doc = _get_owned_document(doc_id, user, db)
    db.delete(doc)
    db.commit()
    return {"status": "deleted"}


# --- Chatbot -------------------------------------------------------------
@app.get("/documents/{doc_id}/messages")
def get_chat_history(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the chat message history for a document."""
    doc = _get_owned_document(doc_id, user, db)
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.document_id == doc.id)
        .order_by(ChatMessage.id.asc())
        .all()
    )
    return {"messages": [m.to_dict() for m in messages]}


@app.post("/documents/{doc_id}/chat", response_model=ChatResponse)
def chat_with_document(
    doc_id: int,
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Chat with the AI assistant about a specific document. The user's question
    and the assistant's reply are both persisted as chat history.

    Note: the extracted document text is retrieved from storage. Since only the
    preview is stored, we reconstruct the full context from the stored analysis
    and preview for the chatbot.
    """
    doc = _get_owned_document(doc_id, user, db)
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    analysis = doc.get_analysis()

    # Load recent conversation to give the model context.
    history_rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.document_id == doc.id)
        .order_by(ChatMessage.id.desc())
        .limit(20)
        .all()
    )
    history = [{"role": m.role, "content": m.content} for m in reversed(history_rows)]

    # Build full text context from preview (the stored raw text is not kept in
    # full; preview is enough for a helpful assistant).
    document_text = doc.text_preview or ""

    try:
        reply = chat_about_document(
            document_text=document_text,
            analysis=analysis,
            question=req.message.strip(),
            history=history,
            target_language=doc.language or "hindi",
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # Persist the two new turns.
    user_msg = ChatMessage(document_id=doc.id, role="user", content=req.message.strip())
    db.add(user_msg)
    db.flush()
    assistant_msg = ChatMessage(document_id=doc.id, role="assistant", content=reply)
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return ChatResponse(reply=reply, reply_id=assistant_msg.id)
