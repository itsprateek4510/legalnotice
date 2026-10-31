import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { uploadPDF } from "../api/api";
import { getErrorDetail } from "../api/api";
import { LANGUAGES } from "../utils/constants";

export default function FileUpload({ onAnalyzed, onError, setLoading, loading }) {
  const handleFile = useCallback(
    async (file, lang) => {
      if (!file) return;

      // Client-side validation
      if (file.type && file.type !== "application/pdf") {
        onError("Only PDF files are supported. Please upload a .pdf document.");
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        onError("File is too large. Maximum allowed size is 10 MB.");
        return;
      }

      setLoading(true);
      try {
        const data = await uploadPDF(file, lang);
        onAnalyzed(data, lang);
      } catch (err) {
        onError(getErrorDetail(err));
      }
    },
    [onAnalyzed, onError, setLoading]
  );

  const onDrop = useCallback(
    (acceptedFiles, rejections) => {
      if (rejections && rejections.length > 0) {
        onError("That file type is not supported. Please upload a PDF file.");
        return;
      }
      const file = acceptedFiles[0];
      if (file) {
        const langSelect = document.getElementById("language-select");
        const lang = langSelect ? langSelect.value : "hindi";
        handleFile(file, lang);
      }
    },
    [handleFile, onError]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    multiple: false,
    maxSize: 10 * 1024 * 1024,
  });

  return (
    <div className="upload-page">
      <div
        {...getRootProps()}
        className={`dropzone ${isDragActive ? "dropzone-active" : ""}`}
        role="button"
        aria-label="Upload a PDF legal notice"
      >
        <input {...getInputProps()} />
        <div className="dropzone-icon" aria-hidden="true">📄</div>
        {isDragActive ? (
          <p>Drop your PDF here…</p>
        ) : (
          <>
            <p className="dropzone-title">
              Drag &amp; drop your legal notice here
            </p>
            <p className="dropzone-subtitle">
              or click to browse files — PDF only, max 10 MB
            </p>
          </>
        )}
      </div>

      <div className="upload-options">
        <label htmlFor="language-select">
          Translation language:
          <select id="language-select" defaultValue="hindi" disabled={loading}>
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => {
            const fileInput = document.querySelector('input[type="file"]');
            if (!fileInput) return;
            const file = fileInput.files && fileInput.files[0];
            const langSelect = document.getElementById("language-select");
            const lang = langSelect ? langSelect.value : "hindi";
            if (file) {
              handleFile(file, lang);
            } else {
              onError("Please select a PDF file first.");
            }
          }}
          disabled={loading}
        >
          {loading ? "Processing…" : "Analyze Document"}
        </button>
      </div>
    </div>
  );
}