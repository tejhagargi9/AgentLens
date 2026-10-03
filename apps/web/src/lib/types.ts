// Mirrors the API's response and SSE event shapes (apps/api/src/agentos/api/routes).

/** The agents in display order, each with the agents that must finish before it starts. */
export const AGENTS = [
  { id: "planner", label: "Planner Agent", after: [] },
  { id: "rag", label: "RAG Agent", after: ["planner"] },
  { id: "github", label: "GitHub Agent", after: ["planner"] },
  { id: "code_analysis", label: "Code Analysis Agent", after: ["rag", "github"] },
  { id: "analyst", label: "Analyst Agent", after: ["code_analysis"] },
  { id: "verifier", label: "Verifier Agent", after: ["analyst"] },
  { id: "report", label: "Report Agent", after: ["verifier"] },
] as const;

export type AgentId = (typeof AGENTS)[number]["id"];

export type EvidenceRef = {
  id: string;
  kind: "document" | "code" | "github";
  source: string;
  location: string;
};

export type VerifiedClaim = {
  statement: string;
  evidence_ids: string[];
  status: "verified" | "needs_review";
  reason: string;
};

/** Per-agent results; which fields are present depends on the agent. */
export type AgentDetail = {
  plan?: string[];
  search_queries?: string[];
  github_tasks?: string[];
  evidence?: EvidenceRef[];
  notes?: string;
  summary?: string;
  gaps?: string[];
  claims?: VerifiedClaim[];
  final_report?: string;
};

export type AgentMetrics = {
  seconds?: number;
  input_tokens?: number;
  output_tokens?: number;
};

export type RunEvent =
  | { type: "node"; node: AgentId; detail: AgentDetail; metrics: AgentMetrics; warnings: string[] }
  | { type: "done" }
  | { type: "error"; message: string };

export type User = { id: string; email: string };

export type SourceKind = "document" | "codebase" | "github";

export type Source = {
  id: string;
  kind: SourceKind;
  name: string;
  size_bytes: number | null;
  status: "pending" | "indexing" | "ready" | "failed";
  error: string | null;
  chunk_count: number | null;
  created_at: string;
};
