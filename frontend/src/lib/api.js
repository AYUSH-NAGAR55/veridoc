const BASE = "/api";

async function handle(res) {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  listDocuments: () => fetch(`${BASE}/documents`).then(handle),
  getDocument: (id) => fetch(`${BASE}/documents/${id}`).then(handle),
  uploadDocument: (file) => {
    const form = new FormData();
    form.append("file", file);
    return fetch(`${BASE}/documents`, { method: "POST", body: form }).then(handle);
  },
  deleteDocument: (id) => fetch(`${BASE}/documents/${id}`, { method: "DELETE" }).then(handle),
  getReviewQueue: () => fetch(`${BASE}/review`).then(handle),
  acceptField: (fieldId) => fetch(`${BASE}/review/${fieldId}/accept`, { method: "POST" }).then(handle),
  correctField: (fieldId, correctedValue) =>
    fetch(`${BASE}/review/${fieldId}/correct`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ corrected_value: correctedValue }),
    }).then(handle),
  ask: (documentId, question) =>
    fetch(`${BASE}/documents/${documentId}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    }).then(handle),
};

export const PROCESSING_STATUSES = ["uploaded", "classifying", "extracting", "validating", "indexing"];

export const STATUS_LABELS = {
  uploaded: "Queued",
  classifying: "Reading pages",
  extracting: "Extracting content",
  validating: "Validating",
  indexing: "Building knowledge base",
  ready: "Ready",
  needs_review: "Needs review",
  failed: "Failed",
};
