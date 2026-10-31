import axios from "axios";
import { API_BASE_URL, AUTH_TOKEN_KEY } from "../utils/constants";

const http = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // LLM calls can take a while
});

// Attach the JWT token to every request when present.
http.interceptors.request.use((config) => {
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

function getErrorDetail(err) {
  const detail = err?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  return err?.message || "Unexpected error. Please try again.";
}

/* ------------------------- Auth ------------------------- */

export async function registerUser({ full_name, email, password }) {
  const { data } = await http.post("/auth/register", {
    full_name,
    email,
    password,
  });
  return data;
}

export async function loginUser({ email, password }) {
  const { data } = await http.post("/auth/login", { email, password });
  return data;
}

export async function fetchMe() {
  const { data } = await http.get("/auth/me");
  return data;
}

/* ----------------------- Documents ---------------------- */

export async function listDocuments({ folderId = null, unfiled = false } = {}) {
  let url = "/documents";
  const params = [];
  if (folderId != null) params.push(`folder_id=${folderId}`);
  if (unfiled) params.push("unfiled=true");
  if (params.length) url += `?${params.join("&")}`;
  const { data } = await http.get(url);
  return data.documents || [];
}

export async function getDocument(docId) {
  const { data } = await http.get(`/documents/${docId}`);
  return data.document;
}

export async function deleteDocument(docId) {
  const { data } = await http.delete(`/documents/${docId}`);
  return data;
}

export async function moveDocument(docId, folderId) {
  const { data } = await http.put(`/documents/${docId}/folder`, {
    folder_id: folderId, // null => unfiled
  });
  return data.document;
}

/* ------------------------- Folders ---------------------- */

export async function listFolders() {
  const { data } = await http.get("/folders");
  return data.folders || [];
}

export async function createFolder(name) {
  const { data } = await http.post("/folders", { name });
  return data.folder;
}

export async function renameFolder(folderId, name) {
  const { data } = await http.patch(`/folders/${folderId}`, { name });
  return data.folder;
}

export async function deleteFolder(folderId) {
  const { data } = await http.delete(`/folders/${folderId}`);
  return data;
}

/**
 * Upload a PDF and retrieve the analysis result.
 * @param {File} file  The PDF file to upload.
 * @param {string} language  Language code for the regional translation.
 */
export async function uploadPDF(file, language = "hindi") {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await http.post(
    `/upload?language=${encodeURIComponent(language)}`,
    formData,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return data;
}

/* ------------------------- Chatbot ---------------------- */

export async function getChatHistory(docId) {
  const { data } = await http.get(`/documents/${docId}/messages`);
  return data.messages || [];
}

export async function sendChatMessage(docId, message) {
  const { data } = await http.post(`/documents/${docId}/chat`, { message });
  return data; // { reply, reply_id }
}

/* ------------------------- Misc -------------------------- */

export async function pingServer() {
  const { data } = await http.get("/ping");
  return data;
}

export { getErrorDetail };