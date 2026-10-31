# Design Documentation

## Court Date & Legal Notice Translator

BCS-554, V Semester, 2026–2027. This document describes the implementation present in the repository, not proposed features.

## 1. Objective and scope

Help users understand text-based legal notices by extracting PDF text, identifying key information with an external LLM, displaying simplified explanations, and supporting document-specific questions. The system provides registration, login, private document storage, and folders. It is not a substitute for a lawyer.

## 2. Architecture

```mermaid
flowchart LR
    U[User / browser] --> R[React frontend]
    R -->|HTTP + Bearer JWT| F[FastAPI backend]
    F --> S[Password hashing and JWT validation]
    F --> P[pdfplumber / pypdf]
    P --> L[LLM prompting and JSON normalization]
    L --> A[Gemini / OpenAI / local Ollama]
    F --> O[SQLAlchemy ORM]
    O --> D[(SQLite app.db)]
    L --> F
```

The browser uses Axios to call FastAPI. Protected routes resolve the current user from a signed JWT. PDF text is extracted in memory. The backend sends up to 12,000 characters to the configured LLM, normalizes its response, and stores the analysis as JSON text. External AI providers may receive document content; use synthetic or anonymized documents for demonstrations.

## 3. Modules

| Module | Responsibility |
|---|---|
| `frontend/src/App.js` | Authentication gate, upload/document views, dashboard state |
| `frontend/src/components/` | Authentication, upload, folders/documents, results and chat UI |
| `frontend/src/api/api.js` | HTTP requests and token attachment |
| `backend/app/main.py` | API routes, validation, ownership checks and persistence |
| `backend/app/database.py` | SQLAlchemy models, sessions and lightweight migration |
| `backend/app/security.py` | bcrypt password hashing and JWT creation/validation |
| `backend/app/pdf_parser.py` | Text-based PDF extraction and validation |
| `backend/app/llm_processor.py` | Provider dispatch, prompts, parsing, normalization and chat |
| `backend/app/models.py` | API request/response schemas |

## 4. Entity relationship diagram

```mermaid
erDiagram
    USERS ||--o{ FOLDERS : owns
    USERS ||--o{ DOCUMENTS : owns
    FOLDERS o|--o{ DOCUMENTS : organizes
    DOCUMENTS ||--o{ CHAT_MESSAGES : contains
    USERS {
        integer id PK
        string email UK
        string full_name
        string hashed_password
        datetime created_at
    }
    FOLDERS {
        integer id PK
        integer user_id FK
        string name
        datetime created_at
    }
    DOCUMENTS {
        integer id PK
        integer user_id FK
        integer folder_id FK
        string filename
        text text_preview
        string language
        text analysis
        datetime created_at
    }
    CHAT_MESSAGES {
        integer id PK
        integer document_id FK
        string role
        text content
        datetime created_at
    }
```

Each document belongs to one user and optionally one folder. `analysis` is JSON serialized into a text column. `text_preview` stores only the first 500 extracted characters (plus an ellipsis when truncated). The original PDF and full extracted text are not persisted. The ORM deletes a document's messages when the document is deleted. Deleting a folder retains its documents as unfiled. These are application/ORM behaviors, not SQL `ON DELETE CASCADE` guarantees. Older SQLite files receive `folder_id` through an `ALTER TABLE` migration without a foreign-key constraint.

## 5. Upload flow

```mermaid
flowchart TD
    A[Register / log in] --> B[Choose PDF and language]
    B --> C[POST /upload with JWT]
    C --> D{Authenticated?}
    D -->|No| E[401 error]
    D -->|Yes| F{PDF extension, nonempty, within size limit?}
    F -->|No| G[400 / 413 error]
    F -->|Yes| H[Extract PDF text]
    H --> I{Readable text?}
    I -->|No| J[400 extraction error]
    I -->|Yes| K[Call configured LLM]
    K --> L[Parse and normalize JSON]
    L --> M[Save document preview and analysis]
    M --> N[Display summary, dates, actions and explanation]
```

## 6. Chat sequence

```mermaid
sequenceDiagram
    actor User
    participant UI as React
    participant API as FastAPI
    participant DB as SQLite
    participant AI as LLM provider
    User->>UI: Ask about saved document
    UI->>API: POST /documents/{id}/chat + JWT
    API->>DB: Resolve user and check document ownership
    DB-->>API: Preview, analysis, recent messages
    API->>AI: Context + question + recent conversation
    AI-->>API: Reply
    API->>DB: Save user and assistant turns
    API-->>UI: Reply and message ID
```

## 7. API summary

Public: `GET /ping`, `POST /auth/register`, `POST /auth/login`.

Protected: `GET /auth/me`; `POST /upload`; `GET /documents`; `GET, DELETE /documents/{id}`; `GET /documents/{id}/messages`; `POST /documents/{id}/chat`; `GET, POST /folders`; `PATCH, DELETE /folders/{id}`; `PUT /documents/{id}/folder`.

Document and folder operations verify ownership. Validation includes PDF extension/signature, empty file, upload size, nonempty folder/chat fields and duplicate email. Interactive API documentation is available at `/docs` while the backend runs.

## 8. Constraints and known limitations

- Scanned/image-only PDFs require OCR, which is not implemented.
- Long notices are truncated for analysis; chat receives only the saved preview and analysis.
- AI output may be inaccurate. Dates and deadlines require comparison with the original notice.
- Malformed AI JSON currently can produce a generic HTTP 500 error.
- Changing the dashboard language does not generate a new translation; select the desired language before upload.
- The development JWT secret must be replaced before deployment.
- Tests mock provider responses: they validate application behavior, not live model quality.

## 9. Evaluation artifacts

- `docs/TEST_CASES.md`: test instructions and scope.
- `docs/TEST_RESULTS.md`: recorded execution results.
- `dataset/README.md`: synthetic data description and evaluation procedure.
- `dataset/expected_results.json`: expected facts for each sample.
- `dataset/pdfs/`: generated text-based sample PDFs.

Mermaid diagrams can be viewed in a Mermaid-capable Markdown viewer or exported using Mermaid Live Editor for a printed report.
