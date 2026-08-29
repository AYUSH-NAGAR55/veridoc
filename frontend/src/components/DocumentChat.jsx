import { useRef, useState, useEffect } from "react";
import { Send, FileSearch, Sparkles } from "lucide-react";
import ConfidenceRing from "./ConfidenceRing";
import { api } from "../lib/api";

const SUGGESTIONS = [
  "What is the total?",
  "Who is the vendor?",
  "What was the revenue?",
];

export default function DocumentChat({ documentId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  async function send(question) {
    const q = (question ?? input).trim();
    if (!q || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setBusy(true);
    try {
      const res = await api.ask(documentId, q);
      setMessages((m) => [...m, { role: "assistant", ...res }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", answer: e.message || "Something went wrong.", confidence: 0 }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-xl2 border border-border bg-surface shadow-soft flex flex-col h-[560px]">
      <div className="px-5 py-4 border-b border-border flex items-center gap-2">
        <FileSearch size={16} className="text-primary-deep" />
        <p className="font-medium text-ink text-sm">Ask this document</p>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center px-6">
            <div className="w-11 h-11 rounded-full bg-primary-soft flex items-center justify-center mb-3">
              <Sparkles size={18} className="text-primary-deep" />
            </div>
            <p className="text-sm text-ink-soft">Ask anything about this document. Answers come with a source page and confidence.</p>
            <div className="mt-4 flex flex-wrap gap-2 justify-center">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="text-xs rounded-full border border-border px-3 py-1.5 text-ink-soft hover:border-primary hover:text-primary-deep transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="flex justify-end">
              <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-primary-soft text-ink px-4 py-2.5 text-sm">
                {m.text}
              </div>
            </div>
          ) : (
            <div key={i} className="flex justify-start">
              <div className="max-w-[85%] rounded-2xl rounded-tl-sm bg-paper border border-border px-4 py-3 text-sm">
                <p className="text-ink">{m.answer}</p>
                {m.source_page && (
                  <div className="mt-2.5 pt-2.5 border-t border-border flex items-center gap-2.5">
                    <ConfidenceRing value={m.confidence} size={30} strokeWidth={3} />
                    <div className="text-[11px] text-ink-soft leading-tight">
                      <p className="font-medium text-ink-soft">Source</p>
                      <p>Page {m.source_page}{m.source_label ? ` — ${m.source_label}` : ""}</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )
        )}

        {busy && (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-tl-sm bg-paper border border-border px-4 py-3 text-sm text-ink-soft">
              <span className="inline-flex gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-ink-soft animate-bounce [animation-delay:-0.3s]" />
                <span className="w-1.5 h-1.5 rounded-full bg-ink-soft animate-bounce [animation-delay:-0.15s]" />
                <span className="w-1.5 h-1.5 rounded-full bg-ink-soft animate-bounce" />
              </span>
            </div>
          </div>
        )}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
        className="border-t border-border p-3 flex items-center gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask anything about this document…"
          className="flex-1 rounded-xl2 border border-border bg-paper px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-soft"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="w-10 h-10 shrink-0 rounded-xl2 bg-primary text-white flex items-center justify-center hover:bg-primary-deep transition-colors disabled:opacity-40"
        >
          <Send size={16} />
        </button>
      </form>
    </div>
  );
}
