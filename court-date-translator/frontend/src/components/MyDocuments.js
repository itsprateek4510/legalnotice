import { useEffect, useState } from "react";
import {
  createFolder,
  deleteDocument,
  deleteFolder,
  listDocuments,
  listFolders,
  moveDocument,
  renameFolder,
} from "../api/api";
import { getErrorDetail } from "../api/api";
import DocumentCard from "./DocumentCard";

/**
 * "My documents" — a user-created folder & file explorer.
 *
 * Root view: list of folders (with doc counts) + the "Unfiled" bucket.
 * Folder view: simplified notice cards for the documents inside a folder.
 */
export default function MyDocuments({ onOpen, refreshKey }) {
  const [folders, setFolders] = useState([]);
  const [docs, setDocs] = useState([]);
  const [mode, setMode] = useState("root"); // "root" | "folder" | "unfiled"
  const [activeFolder, setActiveFolder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);

  const [editingFolderId, setEditingFolderId] = useState(null);
  const [editingName, setEditingName] = useState("");

  // Load folders + relevant documents.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const folderList = await listFolders();
        if (cancelled) return;
        setFolders(folderList);

        let docItems;
        if (mode === "folder" && activeFolder) {
          docItems = await listDocuments({ folderId: activeFolder.id });
        } else if (mode === "unfiled") {
          docItems = await listDocuments({ unfiled: true });
        } else {
          docItems = [];
        }
        if (!cancelled) {
          setDocs(docItems);
          // Re-sync the active folder's count.
          const synced = folderList.find((f) => f.id === activeFolder?.id);
          if (mode === "folder" && activeFolder && synced) {
            setActiveFolder(synced);
          }
        }
      } catch (err) {
        if (!cancelled) setError(getErrorDetail(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey, mode, activeFolder?.id]);

  const loadAll = async () => {
    const folderList = await listFolders();
    setFolders(folderList);
    let docItems = [];
    if (mode === "folder" && activeFolder) {
      docItems = await listDocuments({ folderId: activeFolder.id });
    } else if (mode === "unfiled") {
      docItems = await listDocuments({ unfiled: true });
    }
    setDocs(docItems);
  };

  /* ---- Folder actions ---- */

  const handleCreateFolder = async (e) => {
    e.preventDefault();
    const name = newName.trim();
    if (!name) return;
    setCreating(true);
    setError(null);
    try {
      await createFolder(name);
      setNewName("");
      await loadAll();
    } catch (err) {
      setError(getErrorDetail(err));
    } finally {
      setCreating(false);
    }
  };

  const startRename = (folder) => {
    setEditingFolderId(folder.id);
    setEditingName(folder.name);
  };

  const submitRename = async (e) => {
    e.preventDefault();
    const name = editingName.trim();
    if (!name || !editingFolderId) return;
    try {
      await renameFolder(editingFolderId, name);
      setEditingFolderId(null);
      await loadAll();
    } catch (err) {
      setError(getErrorDetail(err));
    }
  };

  const handleDeleteFolder = async (folder) => {
    const message =
      `Delete folder "${folder.name}"? ` +
      `${folder.document_count} document(s) inside will move to "Unfiled" ` +
      "and won't be deleted.";
    if (!window.confirm(message)) return;
    try {
      await deleteFolder(folder.id);
      if (mode === "folder" && activeFolder?.id === folder.id) setMode("root");
      setActiveFolder(null);
      await loadAll();
    } catch (err) {
      setError(getErrorDetail(err));
    }
  };

  const handleDeleteDoc = async (doc) => {
    if (!window.confirm(`Delete "${doc.filename}" and its conversation?`)) return;
    try {
      await deleteDocument(doc.id);
      await loadAll();
    } catch (err) {
      setError(getErrorDetail(err));
    }
  };

  const handleMoveDoc = async (doc, folderId) => {
    try {
      const updated = await moveDocument(doc.id, folderId);
      // Remove from current listing if it no longer belongs here.
      if (mode === "folder" && activeFolder) {
        if (updated.folder_id !== activeFolder.id) {
          setDocs((prev) => prev.filter((d) => d.id !== doc.id));
          setFolders(await listFolders());
        }
      } else if (mode === "unfiled" && folderId != null) {
        setDocs((prev) => prev.filter((d) => d.id !== doc.id));
        setFolders(await listFolders());
      } else {
        await loadAll();
      }
    } catch (err) {
      setError(getErrorDetail(err));
    }
  };

  const openFolder = (folder) => {
    setActiveFolder(folder);
    setMode("folder");
  };

  const goRoot = () => {
    setActiveFolder(null);
    setMode("root");
    setDocs([]);
  };

  /* ---- Render ---- */

  if (loading) return <p className="muted">Loading your documents…</p>;

  if (error) {
    return <div className="alert alert-danger">{error}</div>;
  }

  return (
    <div className="folders-view">
      {mode !== "root" && (
        <div className="folder-crumb">
          <button type="button" className="btn btn-secondary btn-sm" onClick={goRoot}>
            ← All folders
          </button>
          <span className="folder-name">{activeFolder?.name}</span>
        </div>
      )}

      {/* ---- Root: folders + unfiled ---- */}
      {mode === "root" && (
        <section className="folders-root">
          <form className="new-folder-form" onSubmit={handleCreateFolder}>
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="New folder name (e.g. Court Cases, Bank, Property)…"
              aria-label="New folder name"
              disabled={creating}
            />
            <button
              type="submit"
              className="btn btn-primary"
              disabled={creating || !newName.trim()}
            >
              {creating ? "Adding…" : "＋ New folder"}
            </button>
          </form>

          {folders.length === 0 ? (
            <p className="muted folders-empty">
              No folders yet. Create folders to organize your legal notices —
              for example by case, court, or topic.
            </p>
          ) : (
            <ul className="folder-grid">
              {folders.map((folder) => (
                <li key={folder.id}>
                  <div className="folder-tile" onClick={() => openFolder(folder)}>
                    <span className="folder-icon" aria-hidden="true">📁</span>
                    <div className="folder-info">
                      <span className="folder-tile-name">{folder.name}</span>
                      <span className="folder-tile-count">
                        {folder.document_count} notice
                        {folder.document_count === 1 ? "" : "s"}
                      </span>
                    </div>
                  </div>
                  <div className="folder-tile-actions">
                    {editingFolderId === folder.id ? (
                      <form onSubmit={submitRename} className="rename-row">
                        <input
                          type="text"
                          value={editingName}
                          onChange={(e) => setEditingName(e.target.value)}
                          autoFocus
                          aria-label="Rename folder"
                        />
                        <button type="submit" className="btn btn-sm" title="Save">✓</button>
                        <button
                          type="button"
                          className="btn btn-sm"
                          onClick={() => setEditingFolderId(null)}
                          title="Cancel"
                        >
                          ✕
                        </button>
                      </form>
                    ) : (
                      <>
                        <button
                          type="button"
                          className="btn btn-link"
                          onClick={() => startRename(folder)}
                        >
                          Rename
                        </button>
                        <button
                          type="button"
                          className="btn btn-link-danger"
                          onClick={() => handleDeleteFolder(folder)}
                        >
                          Delete
                        </button>
                      </>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}

          {/* Unfiled bucket */}
          <button type="button" className="unfiled-row" onClick={() => setMode("unfiled")}>
            <span className="folder-icon" aria-hidden="true">🗂️</span>
            <span className="folder-info">
              <span className="folder-tile-name">Unfiled</span>
              <span className="folder-tile-count">
                Documents not inside a folder
              </span>
            </span>
            <span className="btn btn-secondary btn-sm">View</span>
          </button>
        </section>
      )}

      {/* ---- Folder / unfiled contents ---- */}
      {mode !== "root" && (
        <section className="folder-docs">
          {docs.length === 0 ? (
            <p className="muted">
              {mode === "unfiled"
                ? "No unfiled documents."
                : "This folder is empty. Open a document in the dashboard and choose “Save to folder”."}
            </p>
          ) : (
            <div className="doc-card-grid">
              {docs.map((doc) => (
                <DocumentCard
                  key={doc.id}
                  doc={doc}
                  folders={folders}
                  onOpen={onOpen}
                  onMove={handleMoveDoc}
                  onDelete={handleDeleteDoc}
                />
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}