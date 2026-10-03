"use client";

import { useRef, useState } from "react";

import { streamRun } from "@/lib/api";
import { AGENTS, type AgentId } from "@/lib/types";

type Status = "idle" | "running" | "done" | "error";

export function RunConsole() {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [finished, setFinished] = useState<AgentId[]>([]);
  const [report, setReport] = useState("");
  const [error, setError] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setStatus("running");
    setFinished([]);
    setReport("");
    setError("");

    try {
      await streamRun(
        query,
        (runEvent) => {
          if (runEvent.type === "node") {
            setFinished((nodes) => [...nodes, runEvent.node]);
            if (typeof runEvent.update.final_report === "string") {
              setReport(runEvent.update.final_report);
            }
          } else if (runEvent.type === "done") {
            setStatus("done");
          } else {
            setError(runEvent.message);
            setStatus("error");
          }
        },
        controller.signal,
      );
    } catch (err) {
      if (controller.signal.aborted) return;
      setError(err instanceof Error ? err.message : String(err));
      setStatus("error");
    }
  }

  return (
    <div className="grid gap-6 md:grid-cols-[1fr_16rem]">
      <div className="flex flex-col gap-4">
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask about a repository or your documentation…"
            rows={4}
            className="rounded-lg border border-foreground/20 bg-transparent p-3 text-sm outline-none focus:border-foreground/50"
          />
          <button
            type="submit"
            disabled={!query.trim() || status === "running"}
            className="self-start rounded-lg bg-foreground px-4 py-2 text-sm font-medium text-background disabled:opacity-40"
          >
            {status === "running" ? "Running…" : "Run"}
          </button>
        </form>

        {error && (
          <p role="alert" className="rounded-lg border border-red-500/40 p-3 text-sm text-red-500">
            {error}
          </p>
        )}

        {report && (
          <section className="rounded-lg border border-foreground/20 p-4">
            <h3 className="mb-2 text-sm">Report</h3>
            <p className="whitespace-pre-wrap text-sm">{report}</p>
          </section>
        )}
      </div>

      <aside>
        <h3 className="mb-2 text-sm">Execution trace</h3>
        <ol className="flex flex-col gap-1 font-mono text-sm">
          {AGENTS.map((agent) => {
            const isDone = finished.includes(agent.id);
            return (
              <li key={agent.id} className={isDone ? "" : "opacity-40"}>
                {isDone ? "✓" : "·"} {agent.label}
              </li>
            );
          })}
        </ol>
      </aside>
    </div>
  );
}
