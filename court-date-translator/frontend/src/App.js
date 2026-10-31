import { useState } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import AuthPage from "./components/AuthPage";
import FileUpload from "./components/FileUpload";
import Dashboard from "./components/Dashboard";
import MyDocuments from "./components/MyDocuments";
import { MAX_HISTORY, HISTORY_STORAGE_KEY } from "./utils/constants";

function loadHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveHistory(entries) {
  try {
    localStorage.setItem(
      HISTORY_STORAGE_KEY,
      JSON.stringify(entries.slice(0, MAX_HISTORY))
    );
  } catch {
    // Ignore storage quota / private-mode errors.
  }
}

function Shell() {
  const { user, logout } = useAuth();
  const [analysisResult, setAnalysisResult] = useState(null);
  const [currentDocId, setCurrentDocId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [language, setLanguage] = useState("hindi");
  const [history, setHistory] = useState(loadHistory);
  const [refreshDocsKey, setRefreshDocsKey] = useState(0);
  const [view, setView] = useState("upload"); // "upload" | "docs"

  const handleAnalysis = (data, lang) => {
    setAnalysisResult(data);
    setCurrentDocId(data.document_id ?? null);
    setLanguage(lang);
    setLoading(false);
    setError(null);
    setRefreshDocsKey((k) => k + 1);

    const entry = {
      filename: data.filename,
      document_type: data.result?.document_type || "Unknown",
      timestamp: new Date().toISOString(),
      snapshot: data,
    };
    setHistory([entry, ...history].slice(0, MAX_HISTORY));
    saveHistory([entry, ...history].slice(0, MAX_HISTORY));
  };

  const handleOpenDocument = (doc) => {
    // From "My documents": reconstruct the analysis view.
    const snapshot = {
      filename: doc.filename,
      text_preview: doc.text_preview,
      status: "success",
      document_id: doc.id,
      folder_id: doc.folder_id,
      result: doc.result || {},
    };
    setAnalysisResult(snapshot);
    setCurrentDocId(doc.id);
    setLanguage(doc.language || "hindi");
    setError(null);
    setView("upload");
  };

  const handleReset = () => {
    setAnalysisResult(null);
    setCurrentDocId(null);
    setLoading(false);
    setError(null);
    setView("upload");
  };

  const handleLogout = () => {
    logout();
    handleReset();
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <span className="brand-badge" aria-hidden="true">⚖️</span>
          <div className="brand-text">
            <h1>Court Date &amp; Legal Notice Translator</h1>
            <p className="tagline">
              Upload any legal notice or court document and get a clear,
              action-oriented summary in plain English and your language.
            </p>
          </div>
          {user && (
            <div className="user-session">
              <span className="user-avatar" aria-hidden="true">
                {user.full_name ? user.full_name.charAt(0).toUpperCase() : "U"}
              </span>
              <span className="user-name" title={user.email}>
                {user.full_name}
              </span>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={handleLogout}
              >
                Log out
              </button>
            </div>
          )}
        </div>
      </header>

      {loading && (
        <div className="spinner-overlay">
          <div className="spinner" aria-label="Processing document" />
          <p>Analyzing your document… this can take up to a minute.</p>
        </div>
      )}

      <main className="container">
        {!analysisResult ? (
          <>
            <div className="view-tabs">
              <button
                type="button"
                className={`tab ${view === "upload" ? "tab-active" : ""}`}
                onClick={() => setView("upload")}
              >
                Upload new document
              </button>
              <button
                type="button"
                className={`tab ${view === "docs" ? "tab-active" : ""}`}
                onClick={() => setView("docs")}
              >
                My documents
              </button>
            </div>

            {view === "upload" ? (
              <FileUpload
                onAnalyzed={handleAnalysis}
                onError={(msg) => {
                  setError(msg);
                  setLoading(false);
                }}
                setLoading={setLoading}
                loading={loading}
              />
            ) : (
              <MyDocuments
                onOpen={handleOpenDocument}
                refreshKey={refreshDocsKey}
              />
            )}

            {error && !analysisResult && (
              <div className="alert alert-danger" role="alert">
                <strong>Something went wrong:</strong> {error}
              </div>
            )}
          </>
        ) : (
          <Dashboard
            data={analysisResult}
            onReset={handleReset}
            language={language}
            setLanguage={setLanguage}
            docId={currentDocId}
          />
        )}
      </main>

      <footer className="app-footer">
        <p>
          Built for everyday users — not a substitute for legal advice. Please
          consult a lawyer for your specific case.
        </p>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppGate />
    </AuthProvider>
  );
}

function AppGate() {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <Shell /> : <AuthPage />;
}