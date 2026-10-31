import { useEffect, useState } from "react";
import ResultCard from "./ResultCard";
import ChatPanel from "./ChatPanel";
import { listFolders, moveDocument } from "../api/api";
import { getErrorDetail } from "../api/api";
import { LANGUAGES } from "../utils/constants";

function ListItems({ items, emptyText = "None listed." }) {
  if (!items || items.length === 0) {
    return <p className="muted">{emptyText}</p>;
  }
  return (
    <ul>
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ul>
  );
}

export default function Dashboard({
  data,
  onReset,
  language,
  setLanguage,
  docId,
}) {
  const [tab, setTab] = useState("en");
  const [folders, setFolders] = useState([]);
  const [folderError, setFolderError] = useState(null);
  const [currentFolderId, setCurrentFolderId] = useState(() => data.folder_id ?? "");

  // Load available folders for the "Save to folder" control.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const items = await listFolders();
        if (!cancelled) {
          setFolders(items);
          // Keep the select in sync with the document's current folder.
          if (data.folder_id != null && items.some((f) => f.id === data.folder_id)) {
            setCurrentFolderId(data.folder_id);
          } else if (data.folder_id == null) {
            setCurrentFolderId("");
          }
        }
      } catch (err) {
        if (!cancelled) setFolderError(getErrorDetail(err));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [docId, data.folder_id]);

  const result = data?.result || {};

  const handleMove = async (e) => {
    if (!docId) return;
    const value = e.target.value;
    const folderId = value === "" ? null : Number(value);
    const previous = currentFolderId;
    setCurrentFolderId(value);
    setFolderError(null);
    try {
      await moveDocument(docId, folderId);
    } catch (err) {
      setCurrentFolderId(previous);
      setFolderError(getErrorDetail(err));
    }
  };

  const regionalKey =
    language.toLowerCase() === "hindi"
      ? "simplified_explanation_hi"
      : `simplified_explanation_${language.toLowerCase()}`;
  const regionalText =
    result[regionalKey] || result.simplified_explanation_hi;

  const explanationText =
    tab === "hi" ? regionalText : result.simplified_explanation_en;

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div>
          <h2>Analysis complete</h2>
          <p className="muted">
            {data.filename} · Uploaded{" "}
            {data.timestamp
              ? new Date(data.timestamp).toLocaleString()
              : "recently"}
          </p>
        </div>
        <div className="dashboard-actions">
          <label className="inline-label">
            <span>Language:</span>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.label}
                </option>
              ))}
            </select>
          </label>
          {docId && (
            <label className="inline-label">
              <span>Folder:</span>
              <select value={currentFolderId} onChange={handleMove} title="Save to folder">
                <option value="">🗂 Unfiled</option>
                {folders.map((f) => (
                  <option key={f.id} value={f.id}>
                    📁 {f.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          {folderError && <span className="muted folder-error">{folderError}</span>}
          <button type="button" className="btn btn-secondary" onClick={onReset}>
            ← Analyze another document
          </button>
        </div>
      </div>

      {/* Document Summary */}
      <ResultCard title="Document Summary" icon="📋">
        <div className="summary-grid">
          <div className="summary-item">
            <span className="summary-label">Document type</span>
            <span className="summary-value">
              {result.document_type || "—"}
            </span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Court / Authority</span>
            <span className="summary-value">
              {result.court_authority || "—"}
            </span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Case number</span>
            <span className="summary-value">{result.case_number || "—"}</span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Next hearing date</span>
            <span className="summary-value">{result.court_date || "—"}</span>
          </div>
        </div>
        <div className="parties">
          <span className="summary-label">Parties involved</span>
          <ListItems items={result.parties} emptyText="No parties listed." />
        </div>
      </ResultCard>

      {/* Simplified Explanation */}
      <ResultCard title="Simplified Meaning" icon="💡">
        <div className="tabs">
          <button
            type="button"
            className={`tab ${tab === "en" ? "tab-active" : ""}`}
            onClick={() => setTab("en")}
          >
            Plain English
          </button>
          <button
            type="button"
            className={`tab ${tab === "hi" ? "tab-active" : ""}`}
            onClick={() => setTab("hi")}
          >
            {language === "hindi" || language === "english"
              ? "Hindi"
              : LANGUAGES.find((l) => l.code === language)?.label || "Hindi"}
          </button>
        </div>
        <p className="explanation">
          {explanationText ||
            "No explanation available for this section."}
        </p>
      </ResultCard>

      {/* Important Dates */}
      <ResultCard title="Important Dates & Deadlines" icon="🗓️">
        <ListItems items={result.deadlines} emptyText="No specific dates found." />
      </ResultCard>

      {/* Required Action */}
      <ResultCard title="What You Need to Do" icon="✅">
        <ListItems
          items={result.required_actions}
          emptyText="No explicit actions found in the document."
        />
      </ResultCard>

      {/* Action Steps */}
      <ResultCard title="Step-by-Step: What to do next" icon="🪜">
        <ol className="action-steps">
          {result.action_steps && result.action_steps.length > 0 ? (
            result.action_steps.map((step, i) => <li key={i}>{step}</li>)
          ) : (
            <li className="muted">No steps provided.</li>
          )}
        </ol>
      </ResultCard>

      {/* Warnings */}
      <ResultCard title="Warnings & Cautions" icon="⚠️" tone="warning">
        {result.warnings && result.warnings.length > 0 ? (
          <ul>
            {result.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        ) : (
          <p className="muted">
            No critical warnings identified. Still, do not ignore official
            legal documents.
          </p>
        )}
      </ResultCard>

      {/* Optional extracted text preview for transparency */}
      {data.text_preview && (
        <details className="text-preview">
          <summary>View extracted text preview</summary>
          <p className="preview-text">{data.text_preview}</p>
        </details>
      )}

      {/* Per-document AI assistant */}
      {docId ? (
        <ChatPanel docId={docId} />
      ) : (
        <ResultCard title="Ask your document assistant" icon="🤖">
          <p className="muted">
            Re-open this document from "My documents" to chat with the AI
            assistant about it.
          </p>
        </ResultCard>
      )}
    </div>
  );
}