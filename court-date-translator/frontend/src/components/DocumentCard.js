const TYPE_ICONS = {
  Summons: "📜",
  Notice: "📢",
  "Court Order": "⚖️",
  Summon: "📜",
};

/**
 * A compact, simplified "notice card" that shows the most important
 * information about a saved legal document at a glance.
 */
export default function DocumentCard({ doc, folders, onOpen, onMove, onDelete }) {
  const type = doc.document_type || "Document";
  const icon = TYPE_ICONS[type] || "📄";
  const deadlines = doc.deadlines || [];
  const actions = doc.required_actions || [];

  const currentFolderId = doc.folder_id ?? "";
  const canShowDelete = !!onDelete;

  const handleMove = (e) => {
    const value = e.target.value;
    const folderId = value === "" ? null : Number(value);
    if (onMove) onMove(doc, folderId);
    // Reset the select so repeated selections re-trigger change events.
    e.target.value = `${currentFolderId}`;
  };

  return (
    <article className="doc-card">
      <div className="doc-card-head">
        <div className="doc-card-type">
          <span className="doc-card-icon" aria-hidden="true">{icon}</span>
          <span className="doc-card-badge">{type}</span>
        </div>
        <div className="doc-card-actions">
          {onMove && folders && (
            <select
              className="doc-folder-select"
              value={currentFolderId}
              onChange={handleMove}
              aria-label="Move to folder"
              title="Move to folder"
            >
              <option value="">
                {doc.folder_id == null ? "📄 Unfiled" : "Move to…"}
              </option>
              <option value="" disabled>──────────</option>
              <option value="">📂 Unfiled</option>
              {folders.map((f) => (
                <option key={f.id} value={f.id}>
                  📁 {f.name}
                </option>
              ))}
            </select>
          )}
          {canShowDelete && (
            <button
              type="button"
              className="doc-delete"
              onClick={() => onDelete(doc)}
              aria-label="Delete document"
              title="Delete document"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      <button type="button" className="doc-card-body" onClick={() => onOpen(doc)}>
        <h3 className="doc-card-filename" title={doc.filename}>
          {doc.filename}
        </h3>
        <p className="doc-card-date">
          {doc.created_at
            ? `Added ${new Date(doc.created_at).toLocaleDateString()}`
            : ""}
          {doc.case_number ? ` · Case ${doc.case_number}` : ""}
        </p>

        <ul className="doc-card-facts">
          {doc.court_date && (
            <li>
              <span className="fact-label">Next hearing</span>
              <strong>{doc.court_date}</strong>
            </li>
          )}
          {deadlines.length > 0 && (
            <li>
              <span className="fact-label">Deadlines</span>
              <span className="fact-value">
                {deadlines.slice(0, 3).map((d) => (
                  <span key={d} className="fact-tag">
                    {d}
                  </span>
                ))}
                {deadlines.length > 3 ? ` +${deadlines.length - 3} more` : ""}
              </span>
            </li>
          )}
          {actions.length > 0 && (
            <li>
              <span className="fact-label">Required actions</span>
              <span className="fact-value">{actions.length} action(s)</span>
            </li>
          )}
          {!doc.court_date && deadlines.length === 0 && actions.length === 0 && (
            <li className="muted">No action dates listed.</li>
          )}
        </ul>
      </button>

      <div className="doc-card-foot">
        <span className="muted doc-open-hint">Open full details →</span>
      </div>
    </article>
  );
}