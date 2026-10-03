// Mirrors the SSE event shapes emitted by apps/api/src/agentos/api/routes/runs.py.

export const AGENTS = [
  { id: "planner", label: "Planner Agent" },
  { id: "rag", label: "RAG Agent" },
  { id: "github", label: "GitHub Agent" },
  { id: "code_analysis", label: "Code Analysis Agent" },
  { id: "analyst", label: "Analyst Agent" },
  { id: "verifier", label: "Verifier Agent" },
  { id: "report", label: "Report Agent" },
] as const;

export type AgentId = (typeof AGENTS)[number]["id"];

export type RunEvent =
  | { type: "node"; node: AgentId; update: Record<string, unknown> }
  | { type: "done" }
  | { type: "error"; message: string };
