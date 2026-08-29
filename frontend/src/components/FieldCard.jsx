import { CheckCircle2, PencilLine } from "lucide-react";
import ConfidenceRing from "./ConfidenceRing";

const STATUS_LABEL = {
  auto_accepted: "Auto-accepted",
  accepted: "Accepted",
  corrected: "Corrected",
  pending: "Needs review",
};

export default function FieldCard({ field }) {
  const failedNotes = (field.validation_notes || []).filter((n) => !n.passed);

  return (
    <div className="rounded-xl2 border border-border bg-surface p-4 flex items-start gap-4">
      <ConfidenceRing value={field.confidence} size={44} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm font-medium text-ink">{field.field_name}</p>
          <span className="text-[11px] text-ink-soft flex items-center gap-1">
            {field.status === "corrected" ? <PencilLine size={12} /> : field.status !== "pending" ? <CheckCircle2 size={12} className="text-sage" /> : null}
            {STATUS_LABEL[field.status]}
          </span>
        </div>
        <p className="font-mono text-base text-ink mt-1">{field.field_value || "—"}</p>
        {field.source_page && (
          <p className="text-xs text-ink-soft mt-1">Source: Page {field.source_page}</p>
        )}
        {failedNotes.length > 0 && (
          <ul className="mt-2 space-y-0.5">
            {failedNotes.map((n, i) => (
              <li key={i} className="text-xs text-[#8A4A3D] flex gap-1">
                <span>⚠</span> {n.message}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
