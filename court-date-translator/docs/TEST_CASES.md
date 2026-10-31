# Test cases and execution guide

## Automated tests

From `backend/` (after installing the normal application requirements):

```sh
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m unittest discover -s tests -v
```

From `frontend/` (after `npm install`):

```sh
CI=true npm test -- --watchAll=false --runInBand
npm run build
```

If PDFs are missing, first run `python3 dataset/generate_pdfs.py` from the project root. Backend tests use standard-library unittest, existing FastAPI/httpx dependencies, an in-memory SQLite database, fictional accounts and mocked provider responses. No API credits or changes to app.db are required.

| ID | Test / input | Expected behavior | Automated location |
|---|---|---|---|
| U01 | Hash correct and incorrect passwords | No plaintext storage; correct accepts, wrong rejects | `test_password_hash` |
| U02 | JWT creation/decoding | User ID survives roundtrip | `test_token_roundtrip` |
| U03 | JSON, fenced JSON, prose around JSON | Object extracted | `test_json_fences_and_prose` |
| U04 | Malformed model JSON | Parser raises ValueError | `test_invalid_json` |
| U05 | Scalar parties / null deadlines | Normalize to arrays | `test_normalization` |
| U06 | Short / long text | Preserve short text; truncate long text | `test_truncation` |
| U07 | Empty, non-PDF, corrupt PDF | ValueError | `test_invalid_pdf_inputs` |
| U08 | All five synthetic PDFs | Extracted text matches source | `test_extract_all_dataset_pdfs` |
| I01 | Health, no token, invalid token, current user | Health 200; unauthorized 401; correct user | `test_health_and_authentication` |
| I02 | Login, wrong password, duplicate registration | 200, 401, 409 | `test_login_and_duplicate` |
| I03 | Invalid email / blank registration fields | 400 | `test_registration_validation` |
| I04 | Wrong extension / empty PDF / invalid bytes | 400 | `test_invalid_uploads` |
| I05 | File above configured size limit | 413 | `test_upload_size_limit` |
| I06 | Upload, list, retrieve, delete | Analysis persisted; deleted document 404 | `test_document_lifecycle` |
| I07 | Create, rename, move, filter, delete folder | Correct counts; document retained as unfiled | `test_folder_lifecycle_and_filters` |
| I08 | Blank/oversized folder name, blank chat | 400 | `test_empty_folder_and_message` |
| I09 | Other account accesses private objects | 404; private document excluded from listing | `test_cross_user_access` |
| I10 | Chat and delete document | Both chat turns saved then cascade-deleted | `test_chat_persistence_and_cascade_delete` |
| I11 | Provider RuntimeError | Structured 500; no document saved | `test_provider_failure_not_persisted` |
| K01 | Provider returns malformed JSON | Desired: structured JSON error; currently known failing case | `test_known_issue_malformed_ai_has_structured_error` |
| F01 | Default result card | Title, children and default styling | `ResultCard.test.js` |
| F02 | Warning card with icon | Warning style and decorative icon | `ResultCard.test.js` |

K01 is explicitly marked `expectedFailure`, not counted as a passed behavior. It keeps the known defect visible without changing application logic in this documentation/testing task. Subtests exercise multiple inputs but are not counted as separate test methods.

## Manual tests still required

| ID | Procedure | Expected result | Status |
|---|---|---|---|
| M01 | Register/login in a browser, upload a sample using live AI | Facts match dataset; usable UI | Not executed |
| M02 | Select Hindi before upload; review with fluent speaker | Meaning preserved; dates/actions unchanged | Not executed |
| M03 | Reopen saved document after refresh; ask a question | Saved analysis/history available | Not executed |
| M04 | Upload a scanned/image-only PDF | Clear OCR-not-supported error | Not executed |
| M05 | Test mobile-width layout and keyboard navigation | Usable controls without obscured content | Not executed |

Live model quality, OCR edge cases and full browser accessibility are not established by the automated tests. See `TEST_RESULTS.md` for actual execution, not assumed outcomes.
