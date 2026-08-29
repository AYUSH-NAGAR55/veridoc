import { Link } from "react-router-dom";
import { FileText, Trash2 } from "lucide-react";
import StatusBadge from "./StatusBadge";

const DOC_TYPE_LABELS = {
  invoice: "Invoice",
  financial_report: "Financial report",
  generic: "General document",
  unknown: "Processing…",
};

export default function DocumentCard({ doc, onDelete }) {
  return (
    <div className="group relative rounded-xl2 border border-border bg-surface p-5 shadow-soft hover:shadow-lift transition-shadow animate-fadeIn">
      <Link to={`/documents/${doc.id}`} className="block">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-rose-soft flex items-center justify-center shrink-0">
            <FileText size={18} className="text-[#8A4A3D]" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="font-medium text-ink truncate pr-6">{doc.filename}</p>
            <p className="text-xs text-ink-soft mt-0.5">
              {DOC_TYPE_LABELS[doc.doc_type] || doc.doc_type} · {doc.page_count || "…"} page{doc.page_count === 1 ? "" : "s"}
            </p>
          </div>
        </div>
        <div className="mt-4 flex items-center justify-between">
          <StatusBadge status={doc.status} />
          <span className="text-[11px] text-ink-soft">
            {new Date(doc.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
          </span>
        </div>
      </Link>
      <button
        onClick={(e) => {
          e.preventDefault();
          onDelete(doc.id);
        }}
        className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity text-ink-soft hover:text-[#8A4A3D]"
        title="Delete document"
      >
        <Trash2 size={15} />
      </button>
    </div>
  );
}
