"""
Database setup and ORM models.

Uses a lightweight SQLite database via SQLAlchemy (2.x). Four tables:
- users         : registered accounts
- folders       : user-created folders to organize documents
- documents     : uploaded legal notices + their analysis, per user
- chat_messages : AI chatbot conversation history per document
"""

import json
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from .config import settings

DATABASE_URL = settings.DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    documents = relationship(
        "Document", back_populates="owner", cascade="all, delete-orphan"
    )
    folders = relationship(
        "Folder", back_populates="owner", cascade="all, delete-orphan"
    )


class Folder(Base):
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="folders")
    documents = relationship("Document", back_populates="folder")

    def to_dict(self, document_count: int = 0) -> dict:
        """Serialize for API output (optionally with a doc count)."""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "document_count": document_count,
        }


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    folder_id = Column(
        Integer, ForeignKey("folders.id"), nullable=True, index=True
    )
    filename = Column(String, nullable=False)
    text_preview = Column(Text, default="")
    language = Column(String, default="hindi")
    analysis = Column(Text, default="{}")  # JSON-serialized AnalysisResult
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="documents")
    folder = relationship("Folder", back_populates="documents")
    messages = relationship(
        "ChatMessage", back_populates="document", cascade="all, delete-orphan"
    )

    # --- helpers ---------------------------------------------------------
    def get_analysis(self) -> dict:
        """Deserialize the stored analysis JSON."""
        try:
            return json.loads(self.analysis or "{}")
        except json.JSONDecodeError:
            return {}

    def to_dict(self, include_analysis: bool = False) -> dict:
        """Serialize for API output."""
        data = {
            "id": self.id,
            "filename": self.filename,
            "folder_id": self.folder_id,
            "text_preview": self.text_preview,
            "language": self.language,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        # Always include a "simplified preview" of key analysis fields so the
        # frontend can render lightweight notice cards without the full JSON.
        analysis = self.get_analysis()
        data["document_type"] = analysis.get("document_type")
        data["case_number"] = analysis.get("case_number")
        data["court_date"] = analysis.get("court_date")
        data["deadlines"] = analysis.get("deadlines", []) or []
        data["required_actions"] = analysis.get("required_actions", []) or []
        data["warnings"] = analysis.get("warnings", []) or []
        data["parties"] = analysis.get("parties", []) or []
        if include_analysis:
            data["result"] = analysis
        return data


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id"), nullable=False, index=True
    )
    role = Column(String, nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="messages")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


def get_db():
    """FastAPI dependency that yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_schema() -> None:
    """Lightweight migrations for existing databases.

    ``Base.metadata.create_all`` only creates missing *tables*, not missing
    *columns*. Since ``documents.folder_id`` was added later, add it explicitly
    for SQLite databases created before this feature.
    """
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if "documents" in existing_tables:
        cols = {c["name"] for c in inspector.get_columns("documents")}
        if "folder_id" not in cols:
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE documents ADD COLUMN folder_id INTEGER")
                )
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_documents_folder_id "
                        "ON documents (folder_id)"
                    )
                )


def create_all() -> None:
    """Create all tables (idempotent) and run lightweight migrations."""
    Base.metadata.create_all(bind=engine)
    _migrate_schema()
