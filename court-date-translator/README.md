# Court Date & Legal Notice Translator

A full-stack web application that lets users upload a legal notice / court
summons (PDF), automatically extracts the text, runs it through an LLM, and
presents a clear, action-oriented, multilingual summary — with **user accounts**,
**per-document storage**, and a **per-document AI chatbot assistant**.

## Features

### Final-review supporting documents

- [Design documentation: architecture, ER diagram and flows](docs/DESIGN.md)
- [Test cases and rerun commands](docs/TEST_CASES.md)
- [Actual test results and execution logs](docs/TEST_RESULTS.md)
- [Synthetic sample PDF dataset and expected facts](dataset/README.md)

- **User accounts & authentication** (register / login, JWT tokens, bcrypt).
- **Secure per-user storage** (SQLite) — your documents, analyses, and chat
  history are private and only visible to you.
- **PDF upload** with drag-and-drop (via `react-dropzone`) and file validation.
- **Text extraction** with `pdfplumber` (fallback to `pypdf`).
- **LLM analysis** producing structured JSON:
  - Document type, court/authority, parties, case number
  - Next hearing date, deadlines, required actions
  - Simplified explanation in plain English **and** Hindi (or a chosen
    regional language)
  - Step-by-step "What to do next" and critical warnings
- **AI chatbot assistant per document** — ask questions about a specific notice
  ("What should I do first?", "When is the hearing?") and get simple,
  language-aware answers. Conversation is saved per document.
- **"My documents"** — view, reopen, and delete saved analyses.
- **Language selection** — Hindi, Punjabi, Tamil, Telugu, Bengali, Marathi,
  Gujarati, Kannada, Malayalam, English.
- **Three LLM backends**: Google Gemini (default), OpenAI API, and local
  **Ollama**.
- Responsive, calm blue/white dashboard.

## Tech Stack

| Layer      | Technology                                                     |
| ---------- | -------------------------------------------------------------- |
| Frontend   | React 18 (Create React App), Axios, react-dropzone             |
| Backend    | FastAPI (Python 3.9+), Uvicorn, Pydantic v2, CORS              |
| Database   | SQLite + SQLAlchemy 2.x                                        |
| Auth       | JWT (PyJWT) + bcrypt (passlib)                                 |
| PDF        | pdfplumber + pypdf fallback                                    |
| LLM        | Google Gemini (default) / OpenAI / Ollama                      |

## Project Structure

```
court-date-translator/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app, endpoints, CORS, auth, chat
│   │   ├── database.py             # SQLAlchemy engine + User/Document/ChatMessage
│   │   ├── security.py             # bcrypt hashing + JWT helpers
│   │   ├── pdf_parser.py           # PDF text extraction
│   │   ├── llm_processor.py        # Gemini/OpenAI/Ollama prompting + parsing + chat
│   │   ├── models.py               # Pydantic models
│   │   └── config.py               # Environment variables & settings
│   ├── requirements.txt
│   ├── .env.example
│   └── run.py                      # Launches uvicorn
├── frontend/
│   ├── public/index.html
│   ├── src/
│   │   ├── App.js
│   │   ├── index.js
│   │   ├── context/AuthContext.js  # Auth state + login/register/logout
│   │   ├── components/
│   │   │   ├── AuthPage.js         # Login / register screen
│   │   │   ├── FileUpload.js       # Drag & drop upload
│   │   │   ├── Dashboard.js        # Analysis results
│   │   │   ├── ChatPanel.js        # Per-document AI assistant
│   │   │   ├── MyDocuments.js      # Saved documents list
│   │   │   └── ResultCard.js       # Reusable card component
│   │   ├── api/api.js
│   │   ├── styles/App.css
│   │   └── utils/constants.js
│   ├── package.json
│   └── .env
└── README.md
```

## Prerequisites

- **Python 3.9 – 3.12** (Python 3.13/3.14 may not have wheels for
  `pydantic-core`, so 3.12 is recommended)
- **Node.js 16+** and npm

> **Note about the venv in this repo:** the existing `legalnotice/venv` was
> originally created with Python 3.14, which cannot install `pydantic-core`
> (required by FastAPI/pydantic v2). It has been recreated with Python 3.12
> and all backend dependencies installed. Re-run the setup steps below only
> if you move to a different machine.

## Setup & Run

### 1. Backend

```bash
cd backend

# Create the virtual environment (Python 3.9–3.12 recommended)
python3.12 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure your Gemini API key (recommended)
cp .env.example .env
# edit .env and set GEMINI_API_KEY=<your key>
```

Get a free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey).

Run the server:

```bash
python run.py
# or: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000` (docs at `/docs`).

### 2. Frontend

```bash
cd frontend
npm install
npm start
```

Open `http://localhost:3000`, drag a legal notice PDF, and click
**Analyze Document**.

## Using a Local LLM (Ollama)

1. Install [Ollama](https://ollama.com) and pull a model:
   ```bash
   ollama pull llama2
   ```
2. In `backend/.env` set:
   ```env
   LLM_PROVIDER=ollama
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama2
   ```
3. Restart the backend.

## Using OpenAI instead of Gemini

Set `LLM_PROVIDER=openai` and add your OpenAI key to `backend/.env`:
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here
LLM_MODEL=gpt-3.5-turbo
```

## API

All endpoints except `/ping`, `/auth/register`, and `/auth/login` require an
`Authorization: Bearer <token>` header.

| Method | Endpoint                     | Description                                     |
| ------ | ---------------------------- | ------------------------------------------------ |
| GET    | `/ping`                      | Health check (`{"status":"ok"}`)                 |
| POST   | `/auth/register`             | Create account, returns JWT                      |
| POST   | `/auth/login`                | Log in, returns JWT                              |
| GET    | `/auth/me`                   | Current user info                                |
| POST   | `/upload`                    | Multipart PDF upload + `language` query param    |
| GET    | `/documents`                 | List current user's saved documents              |
| GET    | `/documents/{id}`            | Get one document + full analysis                 |
| DELETE | `/documents/{id}`            | Delete a document + its chat history             |
| GET    | `/documents/{id}/messages`   | Chat history for a document                      |
| POST   | `/documents/{id}/chat`       | Ask the AI assistant about a document            |

`POST /upload` accepts:

- `file`: the PDF file (`multipart/form-data`)
- `language`: optional query param, e.g. `hindi`, `punjabi`, `english`
  (default `hindi`)

Response shape:

```json
{
  "filename": "notice.pdf",
  "text_preview": "IN THE COURT OF ...",
  "status": "success",
  "result": {
    "document_type": "Summons",
    "court_authority": "District Court, Greater Noida",
    "parties": ["ABC Pvt Ltd", "XYZ Corp"],
    "case_number": "CS/123/2025",
    "court_date": "2026-01-15",
    "deadlines": ["2025-12-31 for filing reply"],
    "required_actions": ["File written statement within 30 days"],
    "simplified_explanation_en": "This is a summons from the District Court...",
    "simplified_explanation_hi": "यह जिला अदालत से समन है...",
    "warnings": ["Failure to appear may result in ex-parte decision"],
    "action_steps": ["1. Consult a lawyer", "2. File reply before deadline"]
  }
}
```

## Environment Variables

### Backend (`backend/.env`)

| Variable          | Default                         | Description                              |
| ----------------- | ------------------------------- | ---------------------------------------- |
| `LLM_PROVIDER`    | `gemini`                        | `gemini`, `openai`, or `ollama`          |
| `GEMINI_API_KEY`  | (empty)                         | Google Gemini API key                    |
| `GEMINI_MODEL`    | `gemini-3.6-flash`              | Gemini model to use                      |
| `OPENAI_API_KEY`  | (empty)                         | OpenAI API key (only if LLM_PROVIDER=openai) |
| `LLM_MODEL`       | `gpt-3.5-turbo`                 | OpenAI model to use                      |
| `OPENAI_BASE_URL` | (empty)                         | Optional OpenAI-compatible base URL      |
| `USE_LOCAL_LLM`   | `false`                         | Legacy flag; prefer `LLM_PROVIDER=ollama`|
| `OLLAMA_BASE_URL` | `http://localhost:11434`        | Ollama endpoint                          |
| `OLLAMA_MODEL`    | `llama2`                        | Ollama model                             |
| `DATABASE_URL`    | `sqlite:///./app.db`            | SQLAlchemy database URL                  |
| `SECRET_KEY`      | dev default (min 32 chars)      | JWT signing secret — change in production|
| `JWT_EXPIRE_MINUTES`| `1440`                         | JWT lifetime in minutes (1 day)          |
| `PORT`            | `8000`                          | Backend port                             |
| `HOST`            | `0.0.0.0`                       | Backend bind host                        |
| `ALLOWED_ORIGINS` | `http://localhost:3000,...`     | CORS origins (comma-separated)           |
| `MAX_FILE_SIZE`   | `10485760`                      | Max upload size in bytes (10 MB)         |

### Frontend (`frontend/.env`)

| Variable             | Default                 | Description              |
| -------------------- | ----------------------- | ------------------------ |
| `REACT_APP_API_URL`  | `http://localhost:8000` | Backend base URL         |

## Notes & Limitations

- **Scanned/image-based PDFs** cannot be read without OCR. The backend
  returns a clear error message for these.
- **Do not treat output as legal advice** — show it to a qualified lawyer.
- The LLM may occasionally return imperfect output; the backend validates and
  normalizes the JSON before returning it.
- Documents are saved in **SQLite** (`app.db`) on the same machine. For
  production, point `DATABASE_URL` at PostgreSQL e.g.
  `postgresql://user:pass@host:5432/db`.
- The chatbot answers based on the document's extracted text preview, so very
  long or complex filings may produce partial context. For best results, keep
  questions focused on the notice itself.
