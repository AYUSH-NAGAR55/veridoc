import { Check, Loader2 } from "lucide-react";

const STEPS = [
  { key: "classifying", label: "Reading pages" },
  { key: "extracting", label: "Extracting content" },
  { key: "validating", label: "Validating" },
  { key: "indexing", label: "Building knowledge base" },
];

export default function PipelineProgress({ status }) {
  const order = ["uploaded", "classifying", "extracting", "validating", "indexing", "ready"];
  const currentIdx = order.indexOf(status === "needs_review" ? "ready" : status);

  return (
    <div className="rounded-xl2 border border-border bg-surface p-6 shadow-soft">
      <p className="text-sm font-medium text-ink mb-5">Processing this document</p>
      <div className="flex items-center">
        {STEPS.map((step, i) => {
          const stepIdx = order.indexOf(step.key);
          const done = currentIdx > stepIdx;
          const active = currentIdx === stepIdx;
          return (
            <div key={step.key} className="flex items-center flex-1 last:flex-none">
              <div className="flex flex-col items-center gap-2">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center border-2 transition-colors ${
                    done
                      ? "bg-sage border-sage text-white"
                      : active
                      ? "border-primary bg-primary-soft text-primary-deep"
                      : "border-border bg-paper text-ink-soft"
                  }`}
                >
                  {done ? <Check size={15} /> : active ? <Loader2 size={14} className="animate-spin" /> : <span className="text-xs">{i + 1}</span>}
                </div>
                <span className={`text-[11px] text-center w-20 ${active ? "text-ink font-medium" : "text-ink-soft"}`}>
                  {step.label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div className={`h-0.5 flex-1 mx-1 rounded ${done ? "bg-sage" : "bg-border"}`} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
