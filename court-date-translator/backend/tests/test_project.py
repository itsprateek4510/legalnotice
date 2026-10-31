"""Offline tests: isolated SQLite, synthetic PDFs and mocked external AI."""

import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

# Set before importing the application: create_all() must not touch app.db.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.llm_processor import _normalize_result, _parse_json_response, _truncate
from app.pdf_parser import extract_text_from_pdf
from app.security import decode_access_token, hash_password, verify_password


ROOT = Path(__file__).resolve().parents[2]
SAMPLES = json.loads((ROOT / "dataset/expected_results.json").read_text())


class UnitTests(unittest.TestCase):
    def test_password_hash(self):
        hashed = hash_password("demo-password")
        self.assertNotEqual(hashed, "demo-password")
        self.assertTrue(verify_password("demo-password", hashed))
        self.assertFalse(verify_password("wrong", hashed))

    def test_token_roundtrip(self):
        token = main.create_access_token(42, "demo@example.com")
        self.assertEqual(decode_access_token(token)["sub"], "42")

    def test_json_fences_and_prose(self):
        for raw in ['{"parties": []}', '```json\n{"parties": []}\n```', 'Here: {"parties": []}']:
            with self.subTest(raw=raw):
                self.assertEqual(_parse_json_response(raw), {"parties": []})

    def test_invalid_json(self):
        with self.assertRaises(ValueError):
            _parse_json_response("not JSON")

    def test_normalization(self):
        result = _normalize_result({"parties": "Demo", "deadlines": None}, "hindi")
        self.assertEqual(result["parties"], ["Demo"])
        self.assertEqual(result["deadlines"], [])

    def test_truncation(self):
        self.assertEqual(_truncate("short", 10), "short")
        self.assertTrue(_truncate("a" * 20, 10).startswith("a" * 10 + "\n"))

    def test_invalid_pdf_inputs(self):
        for content in [b"", b"not a PDF", b"%PDF-corrupt"]:
            with self.subTest(content=content), self.assertRaises(ValueError):
                extract_text_from_pdf(content)

    def test_extract_all_dataset_pdfs(self):
        for sample in SAMPLES:
            with self.subTest(filename=sample["filename"]):
                actual = extract_text_from_pdf((ROOT / "dataset/pdfs" / sample["filename"]).read_bytes())
                self.assertEqual(" ".join(actual.split()), " ".join(sample["text"].split()))


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        main.database.Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine)

        def override_db():
            with self.sessions() as db:
                yield db

        main.app.dependency_overrides[main.get_db] = override_db
        self.client = TestClient(main.app, raise_server_exceptions=False)
        self.user = {"full_name": "Demo User", "email": "demo@example.com", "password": "DemoPassword123!"}
        response = self.client.post("/auth/register", json=self.user)
        self.assertEqual(response.status_code, 200, response.text)
        self.headers = {"Authorization": "Bearer " + response.json()["access_token"]}

    def tearDown(self):
        self.client.close()
        main.app.dependency_overrides.clear()
        self.engine.dispose()

    def upload(self):
        content = (ROOT / "dataset/pdfs" / SAMPLES[0]["filename"]).read_bytes()
        with patch.object(main, "analyze_legal_document", return_value={"document_type": "Summons", "court_date": "2026-12-15"}):
            response = self.client.post("/upload", headers=self.headers, files={"file": ("demo.pdf", content, "application/pdf")})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["document_id"]

    def test_health_and_authentication(self):
        self.assertEqual(self.client.get("/ping").json(), {"status": "ok"})
        self.assertEqual(self.client.get("/documents").status_code, 401)
        self.assertEqual(self.client.get("/documents", headers={"Authorization": "Bearer invalid"}).status_code, 401)
        self.assertEqual(self.client.get("/auth/me", headers=self.headers).json()["email"], self.user["email"])

    def test_login_and_duplicate(self):
        credentials = {"email": self.user["email"], "password": self.user["password"]}
        self.assertEqual(self.client.post("/auth/login", json=credentials).status_code, 200)
        credentials["password"] = "wrong"
        self.assertEqual(self.client.post("/auth/login", json=credentials).status_code, 401)
        self.assertEqual(self.client.post("/auth/register", json=self.user).status_code, 409)

    def test_registration_validation(self):
        for change in [{"email": "invalid"}, {"full_name": " "}, {"password": ""}]:
            with self.subTest(change=change):
                self.assertEqual(self.client.post("/auth/register", json={**self.user, **change}).status_code, 400)

    def test_invalid_uploads(self):
        for filename, content in [("demo.txt", b"text"), ("empty.pdf", b""), ("invalid.pdf", b"invalid")]:
            with self.subTest(filename=filename):
                self.assertEqual(self.client.post("/upload", headers=self.headers, files={"file": (filename, content)}).status_code, 400)

    def test_upload_size_limit(self):
        with patch.object(main.settings, "MAX_FILE_SIZE", 3):
            response = self.client.post("/upload", headers=self.headers, files={"file": ("large.pdf", b"%PDF-too-large")})
        self.assertEqual(response.status_code, 413)

    def test_document_lifecycle(self):
        did = self.upload()
        self.assertEqual(len(self.client.get("/documents", headers=self.headers).json()["documents"]), 1)
        doc = self.client.get(f"/documents/{did}", headers=self.headers).json()["document"]
        self.assertEqual(doc["result"]["court_date"], "2026-12-15")
        self.assertEqual(self.client.delete(f"/documents/{did}", headers=self.headers).status_code, 200)
        self.assertEqual(self.client.get(f"/documents/{did}", headers=self.headers).status_code, 404)

    def test_folder_lifecycle_and_filters(self):
        did = self.upload()
        response = self.client.post("/folders", headers=self.headers, json={"name": "Demo"})
        self.assertEqual(response.status_code, 200)
        fid = response.json()["folder"]["id"]
        self.assertEqual(self.client.patch(f"/folders/{fid}", headers=self.headers, json={"name": "Renamed"}).status_code, 200)
        self.assertEqual(self.client.put(f"/documents/{did}/folder", headers=self.headers, json={"folder_id": fid}).status_code, 200)
        self.assertEqual(len(self.client.get(f"/documents?folder_id={fid}", headers=self.headers).json()["documents"]), 1)
        self.assertEqual(self.client.get("/documents?unfiled=true", headers=self.headers).json()["documents"], [])
        self.assertEqual(self.client.get("/folders", headers=self.headers).json()["folders"][0]["document_count"], 1)
        self.assertEqual(self.client.delete(f"/folders/{fid}", headers=self.headers).status_code, 200)
        self.assertIsNone(self.client.get(f"/documents/{did}", headers=self.headers).json()["document"]["folder_id"])

    def test_empty_folder_and_message(self):
        self.assertEqual(self.client.post("/folders", headers=self.headers, json={"name": " "}).status_code, 400)
        self.assertEqual(self.client.post("/folders", headers=self.headers, json={"name": "x" * 61}).status_code, 400)
        did = self.upload()
        self.assertEqual(self.client.post(f"/documents/{did}/chat", headers=self.headers, json={"message": " "}).status_code, 400)

    def test_cross_user_access(self):
        did = self.upload()
        fid = self.client.post("/folders", headers=self.headers, json={"name": "Private"}).json()["folder"]["id"]
        other = self.client.post("/auth/register", json={**self.user, "email": "other@example.com"}).json()
        headers = {"Authorization": "Bearer " + other["access_token"]}
        for method, url, kwargs in [
            ("get", f"/documents/{did}", {}),
            ("delete", f"/documents/{did}", {}),
            ("get", f"/documents/{did}/messages", {}),
            ("post", f"/documents/{did}/chat", {"json": {"message": "Hi"}}),
            ("delete", f"/folders/{fid}", {}),
        ]:
            with self.subTest(url=url, method=method):
                self.assertEqual(getattr(self.client, method)(url, headers=headers, **kwargs).status_code, 404)
        self.assertEqual(self.client.get("/documents", headers=headers).json()["documents"], [])

    def test_chat_persistence_and_cascade_delete(self):
        did = self.upload()
        with patch.object(main, "chat_about_document", return_value="The hearing is 15 December 2026."):
            response = self.client.post(f"/documents/{did}/chat", headers=self.headers, json={"message": "When?"})
        self.assertEqual(response.status_code, 200)
        messages = self.client.get(f"/documents/{did}/messages", headers=self.headers).json()["messages"]
        self.assertEqual([m["role"] for m in messages], ["user", "assistant"])
        self.assertEqual(messages[1]["content"], response.json()["reply"])
        self.client.delete(f"/documents/{did}", headers=self.headers)
        with self.sessions() as db:
            self.assertEqual(db.query(main.ChatMessage).count(), 0)

    def test_provider_failure_not_persisted(self):
        content = (ROOT / "dataset/pdfs" / SAMPLES[0]["filename"]).read_bytes()
        with patch.object(main, "analyze_legal_document", side_effect=RuntimeError("Provider unavailable")):
            response = self.client.post("/upload", headers=self.headers, files={"file": ("demo.pdf", content)})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "Provider unavailable")
        self.assertEqual(self.client.get("/documents", headers=self.headers).json()["documents"], [])

    @unittest.expectedFailure
    def test_known_issue_malformed_ai_has_structured_error(self):
        """Known defect: malformed AI JSON currently returns plain generic 500."""
        content = (ROOT / "dataset/pdfs" / SAMPLES[0]["filename"]).read_bytes()
        with patch("app.llm_processor._call_llm", return_value="not valid JSON"):
            response = self.client.post("/upload", headers=self.headers, files={"file": ("demo.pdf", content)})
        self.assertTrue(response.headers.get("content-type", "").startswith("application/json"))


if __name__ == "__main__":
    unittest.main()
