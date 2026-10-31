# Recorded Test Results

Execution date: 29 October 2026. Environment: macOS, existing Python 3.12 virtual environment and installed frontend dependencies.

## Summary

| Suite | Executed | Passed | Known expected failures | Unexpected failures/errors |
|---|---:|---:|---:|---:|
| Backend unittest | 20 | 19 | 1 | 0 |
| Frontend Jest rendering tests | 2 | 2 | 0 | 0 |
| Total | 22 | 21 | 1 | 0 |

Both test commands exited with code 0. The backend's successful process exit includes an explicitly declared expected failure; it does **not** mean every tested behavior is correct.

## Evidence and scope

- Full backend output: [`test-logs/backend.txt`](test-logs/backend.txt).
- Full frontend output: [`test-logs/frontend.txt`](test-logs/frontend.txt).
- Case descriptions and rerun commands: [`TEST_CASES.md`](TEST_CASES.md).
- PDF extraction matched the source text for all five generated samples, ignoring whitespace differences.
- API integration tests used a fresh in-memory SQLite database per test. Existing app.db files were not used.
- AI responses and provider failures were mocked. No live provider requests were made and no live accuracy score is claimed.
- Frontend tests use React static rendering in a Node test environment. They do not exercise browser clicks, network flows or layout. The initial DOM-based attempt was blocked by an unrelated ancestor-directory native `canvas` dependency; static rendering avoids that dependency without changing application code.
- During the preceding audit, the frontend production build also compiled successfully. The test logs linked here cover the newly saved test suites, not that earlier build.

## Known failing case K01

`test_known_issue_malformed_ai_has_structured_error` feeds malformed JSON through the real analysis parser and upload route, while mocking only the external provider call. Desired behavior is a structured JSON error. Actual behavior is HTTP 500 with generic plain-text `Internal Server Error`. It is marked `unittest.expectedFailure` and remains unfixed in this task.

## Warnings observed

- Existing SQLAlchemy timestamp defaults use deprecated `datetime.utcnow()` on Python 3.12.
- The intentional corrupt-PDF test emits an EOF warning from pypdf.

## Not executed / not established

Live Gemini/OpenAI/Ollama responses; legal or translation accuracy; complete browser end-to-end flow; scanned-PDF manual demonstration; mobile/accessibility checks; performance/security penetration testing. Use the manual checklist and dataset procedure before presenting those as verified.
