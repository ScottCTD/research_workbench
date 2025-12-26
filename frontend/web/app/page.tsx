"use client";

import { useState } from "react";
import { ResearchCanvas } from "@/components/canvas/ResearchCanvas";
import { startResearch } from "@/lib/api";
import { ArrowRight, Loader2, Sparkles, StopCircle } from "lucide-react";

export default function Home() {
  const [query, setQuery] = useState("");
  const [runId, setRunId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<{ role: string, content: string }[]>([]);

  const handleStart = async () => {
    if (!query.trim()) return;
    const currentQuery = query;
    setQuery(""); // Clear immediately for UX

    // If not started, we start a new run
    if (!runId) {
      setLoading(true);
      try {
        const id = await startResearch(currentQuery);
        setRunId(id);
        setMessages([{ role: "user", content: currentQuery }]);
      } catch (e) {
        console.error(e);
        alert("Failed to start research");
        setQuery(currentQuery); // Restore on error
      } finally {
        setLoading(false);
      }
    } else {
      // Continue existing run
      setMessages(prev => [...prev, { role: "user", content: currentQuery }]);
    }
  };

  return (
    <main className="flex h-screen w-full flex-col bg-slate-50 text-gray-900 overflow-hidden font-sans">
      {/* Header */}
      <header className="z-10 flex h-14 w-full items-center justify-between border-b border-gray-200 bg-white px-4 shadow-sm">
        <div className="flex items-center gap-2">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-600 text-white shadow-blue-200">
            <Sparkles size={16} />
          </div>
          <h1 className="text-sm font-semibold tracking-tight text-gray-800">Research Workbench</h1>
        </div>
        <div className="flex items-center gap-4 text-xs">
          {runId ? (
            <span className="font-mono text-gray-400">ID: {runId.slice(0, 8)}</span>
          ) : (
            <span className="text-gray-400">Ready to start</span>
          )}
        </div>
      </header>

      {/* Canvas Area */}
      <div className="relative flex-1 overflow-hidden bg-[#FAFBFC]">
        <ResearchCanvas runId={runId} messages={messages} />

        {/* Floating Input Bar */}
        <div className="absolute bottom-6 left-0 right-0 z-20 flex justify-center px-4">
          <div className="w-full max-w-3xl bg-white rounded-2xl border border-gray-200 shadow-xl p-2 flex items-center gap-2 transition-all focus-within:ring-2 focus-within:ring-blue-100 focus-within:border-blue-300">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleStart()}
              placeholder={runId ? "Ask follow-up question..." : "Enter a research topic to begin..."}
              className="flex-1 bg-transparent px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none"
              autoFocus
            />
            <button
              onClick={() => handleStart()}
              disabled={(!runId && loading) || !query.trim()}
              className="p-2.5 rounded-xl bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:hover:bg-blue-600 transition-colors shadow-sm"
            >
              {loading && !runId ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}
