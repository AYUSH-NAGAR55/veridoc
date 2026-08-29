import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import UploadDropzone from "../components/UploadDropzone";
import DocumentCard from "../components/DocumentCard";
import { api, PROCESSING_STATUSES } from "../lib/api";

export default function DocumentsPage({ documents, setDocuments }) {
  const navigate = useNavigate();

  useEffect(() => {
    const hasProcessing = documents.some((d) => PROCESSING_STATUSES.includes(d.status));
    if (!hasProcessing) return;
    const t = setInterval(async () => {
      const fresh = await api.listDocuments();
      setDocuments(fresh);
    }, 2500);
    return () => clearInterval(t);
  }, [documents, setDocuments]);

  async function handleUpload(file) {
    const doc = await api.uploadDocument(file);
    setDocuments((prev) => [doc, ...prev]);
    navigate(`/documents/${doc.id}`);
  }

  async function handleDelete(id) {
    await api.deleteDocument(id);
    setDocuments((prev) => prev.filter((d) => d.id !== id));
  }

  return (
    <div className="max-w-5xl mx-auto px-8 py-10">
      <div className="mb-8">
        <h1 className="font-display text-3xl text-ink">Documents</h1>
        <p className="text-ink-soft mt-1.5">
          Upload a PDF and VeriDoc will understand it page by page, extract what matters, and verify it before it becomes searchable.
        </p>
      </div>

      <div className="mb-10">
        <UploadDropzone onUpload={handleUpload} />
      </div>

      {documents.length === 0 ? (
        <div className="text-center py-16 text-ink-soft text-sm">No documents yet. Upload your first PDF above.</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {documents.map((doc) => (
            <DocumentCard key={doc.id} doc={doc} onDelete={handleDelete} />
          ))}
        </div>
      )}
    </div>
  );
}
