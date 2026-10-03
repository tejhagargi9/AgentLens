"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { ApiError, streamRun } from "@/lib/api";
import { AGENTS, type AgentDetail, type AgentId, type AgentMetrics } from "@/lib/types";

type Status = "idle" | "running" | "done" | "error";
type AgentResult = { detail: AgentDetail; metrics: AgentMetrics };
type Results = Partial<Record<AgentId, AgentResult>>;

/** One line under each finished agent saying what it produced. */
function describe(id: AgentId, detail: AgentDetail): string {
  const count = (n: number, noun: string) => `${n} ${noun}${n === 1 ? "" : "s"}`;
  switch (id) {
    case "planner":
      return count(detail.plan?.length ?? 0, "task");
    case "rag":
      return count(detail.evidence?.length ?? 0, "chunk") + " retrieved";
    case "github":
      return count(detail.evidence?.length ?? 0, "tool result");
    case "code_analysis":
      return detail.notes ? "code analysed" : "no code to analyse";
    case "analyst":
      return detail.summary ? "findings drafted" : "no evidence to analyse";
    case "verifier": {
      const claims = detail.claims ?? [];
      const verified = claims.filter((claim) => claim.status === "verified").length;
      return `${verified} verified, ${claims.length - verified} need review`;
    }
    case "report":
      return "report written";
  }
}

export function RunConsole() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [results, setResults] = useState<Results>({});
  const [warnings, setWarnings] = useState<string[]>([]);
  const [error, setError] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setStatus("running");
    setResults({});
    setWarnings([]);
    setError("");

    try {
      await streamRun(
        query,
        (runEvent) => {
          if (runEvent.type === "node") {
            const { node, detail, metrics } = runEvent;
            setResults((current) => ({ ...current, [node]: { detail, metrics } }));
            if (runEvent.warnings.length > 0) {
              setWarnings((current) => [...current, ...runEvent.warnings]);
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
      if (err instanceof ApiError && err.status === 401) router.replace("/login");
      setError(err instanceof Error ? err.message : String(err));
      setStatus("error");
    }
  }

  const plan = results.planner?.detail.plan ?? [];
  const claims = results.verifier?.detail.claims ?? [];
  const evidence = [
    ...(results.rag?.detail.evidence ?? []),
    ...(results.github?.detail.evidence ?? []),
  ];
  const report = results.report?.detail.final_report ?? "";

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_18rem]">
      <div className="flex min-w-0 flex-col gap-5">
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <label htmlFor="question" className="sr-only">
            Question
          </label>
          <textarea
            id="question"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask about a repository or your documentation…"
            rows={4}
            maxLength={4000}
            className="rounded-lg border border-line bg-surface p-3.5 text-sm outline-none transition-colors placeholder:text-muted/60 focus:border-accent/70"
          />
          <button
            type="submit"
            disabled={!query.trim() || status === "running"}
            className="self-start rounded-full bg-accent px-6 py-2.5 font-subheading text-sm font-medium text-background transition-opacity hover:opacity-85 disabled:opacity-40"
          >
            {status === "running" ? "Running…" : "Run"}
          </button>
        </form>

        {error && (
          <p role="alert" className="rounded-lg border border-red-400/40 bg-red-400/10 p-3.5 text-sm text-red-300">
            {error}
          </p>
        )}

        {warnings.map((warning) => (
          <p key={warning} className="rounded-lg border border-amber-300/30 bg-amber-300/10 p-3.5 text-sm text-amber-200">
            {warning}
          </p>
        ))}

        {plan.length > 0 && !report && (
          <section className="rounded-2xl border border-line p-5">
            <h3 className="text-sm">Plan</h3>
            <ol className="mt-3 list-decimal space-y-1.5 pl-5 text-sm text-muted">
              {plan.map((task) => (
                <li key={task}>{task}</li>
              ))}
            </ol>
          </section>
        )}

        {report && (
          <article className="report rounded-2xl border border-line bg-surface p-6">
            <Markdown remarkPlugins={[remarkGfm]}>{report}</Markdown>
          </article>
        )}

        {claims.length > 0 && (
          <section className="rounded-2xl border border-line">
            <h3 className="border-b border-line px-5 py-4 text-sm">Verification</h3>
            <ul className="divide-y divide-line">
              {claims.map((claim) => {
                const verified = claim.status === "verified";
                return (
                  <li key={claim.statement} className="px-5 py-4">
                    <p className="text-sm">{claim.statement}</p>
                    <p className="mt-2 flex flex-wrap items-center gap-2 font-mono text-[11px] text-muted">
                      <span
                        className={`rounded-full px-2 py-0.5 ${verified ? "bg-accent/15 text-accent" : "bg-amber-300/15 text-amber-200"}`}
                      >
                        {verified ? "verified" : "needs review"}
                      </span>
                      {claim.evidence_ids.map((id) => (
                        <span key={id}>[{id}]</span>
                      ))}
                    </p>
                    <p className="mt-1.5 text-xs text-muted">{claim.reason}</p>
                  </li>
                );
              })}
            </ul>
          </section>
        )}
      </div>

      <aside className="flex flex-col gap-6">
        <div>
          <h3 className="mb-3 text-sm">Execution trace</h3>
          <ol className="flex flex-col gap-3 font-mono text-xs">
            {AGENTS.map((agent) => {
              const result = results[agent.id];
              const isRunning =
                status === "running" && !result && agent.after.every((id) => results[id]);
              return (
                <li key={agent.id} className={result || isRunning ? "" : "opacity-40"}>
                  <p className="flex items-baseline justify-between gap-2">
                    <span>
                      <span className={result ? "text-accent" : ""}>
                        {result ? "✓" : isRunning ? "›" : "·"}
                      </span>{" "}
                      {agent.label}
                    </span>
                    {result?.metrics.seconds !== undefined && (
                      <span className="text-muted">{result.metrics.seconds}s</span>
                    )}
                  </p>
                  <p className="mt-0.5 pl-4 text-[11px] text-muted">
                    {result ? describe(agent.id, result.detail) : isRunning ? "working…" : ""}
                  </p>
                </li>
              );
            })}
          </ol>
        </div>

        {evidence.length > 0 && (
          <div>
            <h3 className="mb-3 text-sm">Evidence</h3>
            <ul className="flex flex-col gap-2 font-mono text-[11px] text-muted">
              {evidence.map((item) => (
                <li key={item.id} className="break-words">
                  <span className="text-accent">[{item.id}]</span> {item.source}
                  <br />
                  <span className="pl-1">{item.location}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </aside>
    </div>
  );
}
