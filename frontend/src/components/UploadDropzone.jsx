import { useCallback, useRef, useState } from "react";
import { UploadCloud, Loader2 } from "lucide-react";

export default function UploadDropzone({ onUpload }) {
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef(null);

  const handleFiles = useCallback(
    async (files) => {
      const file = files?.[0];
      if (!file) return;
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        setError("VeriDoc only reads PDF files right now.");
        return;
      }
      setError("");
      setBusy(true);
      try {
        await onUpload(file);
      } catch (e) {
        setError(e.message || "Upload failed.");
      } finally {
        setBusy(false);
      }
    },
    [onUpload]
  );

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        className={`cursor-pointer rounded-xl2 border-2 border-dashed px-8 py-12 text-center transition-colors ${
          dragging ? "border-primary bg-primary-soft/40" : "border-border bg-surface hover:border-primary/60"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
        <div className="mx-auto w-12 h-12 rounded-full bg-primary-soft flex items-center justify-center mb-4">
          {busy ? (
            <Loader2 size={22} className="text-primary-deep animate-spin" />
          ) : (
            <UploadCloud size={22} className="text-primary-deep" />
          )}
        </div>
        <p className="font-medium text-ink">
          {busy ? "Uploading…" : "Drop a PDF here, or click to choose one"}
        </p>
        <p className="text-sm text-ink-soft mt-1">
          Scanned pages, tables, and messy formatting are all fine — that's what VeriDoc is for.
        </p>
      </div>
      {error && <p className="mt-3 text-sm text-[#8A4A3D]">{error}</p>}
    </div>
  );
}
