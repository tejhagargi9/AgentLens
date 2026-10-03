import type { RunEvent, Source, User } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

/** Turns a FastAPI error body (`detail` string or validation list) into one readable message. */
async function errorMessage(response: Response): Promise<string> {
  try {
    const { detail } = await response.json();
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => String(item.msg).replace(/^Value error, /, "")).join(". ");
    }
  } catch {
    // fall through to the generic message
  }
  return `Request failed (${response.status})`;
}

/** Calls the API with the session cookie attached; throws ApiError on any failure. */
async function request(path: string, init?: RequestInit): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/v1${path}`, { ...init, credentials: "include" });
  } catch (error) {
    if (init?.signal?.aborted) throw error;
    throw new ApiError(0, "Could not reach the server. Check your connection and try again.");
  }
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response));
  return response;
}

function json(body: unknown): RequestInit {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export async function signup(email: string, password: string): Promise<User> {
  return (await request("/auth/signup", json({ email, password }))).json();
}

export async function login(email: string, password: string): Promise<User> {
  return (await request("/auth/login", json({ email, password }))).json();
}

export async function logout(): Promise<void> {
  await request("/auth/logout", { method: "POST" });
}

export async function listSources(): Promise<Source[]> {
  return (await request("/sources")).json();
}

export async function uploadSource(kind: "document" | "codebase", file: File): Promise<Source> {
  const form = new FormData();
  form.append("kind", kind);
  form.append("file", file);
  return (await request("/sources/upload", { method: "POST", body: form })).json();
}

export async function connectGithub(repository: string, token: string): Promise<Source> {
  return (await request("/sources/github", json({ repository, token }))).json();
}

export async function reindexSource(id: string): Promise<Source> {
  return (await request(`/sources/${id}/reindex`, { method: "POST" })).json();
}

export async function deleteSource(id: string): Promise<void> {
  await request(`/sources/${id}`, { method: "DELETE" });
}

/**
 * Starts an agent run and calls `onEvent` for each server-sent event.
 * Uses fetch rather than EventSource because the run is started with a POST body.
 */
export async function streamRun(
  query: string,
  onEvent: (event: RunEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await request("/runs/stream", { ...json({ query }), signal });
  if (!response.body) throw new ApiError(response.status, "The server sent an empty response");

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    // SSE frames are separated by a blank line; keep any trailing partial frame.
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const data = frame
        .split("\n")
        .filter((line) => line.startsWith("data: "))
        .map((line) => line.slice("data: ".length))
        .join("\n");
      if (data) onEvent(JSON.parse(data) as RunEvent);
    }
  }
}
