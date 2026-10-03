"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  ApiError,
  connectGithub,
  deleteSource,
  listSources,
  reindexSource,
  uploadSource,
} from "@/lib/api";
import type { Source, SourceKind } from "@/lib/types";
import {
  UPLOAD_LIMITS,
  validateGithubToken,
  validateRepository,
  validateUpload,
} from "@/lib/validation";

const KIND_LABEL: Record<SourceKind, string> = {
  document: "Document",
  codebase: "Codebase",
  github: "GitHub",
};

const CARD = "flex flex-col rounded-2xl border border-line bg-surface p-6";
const INPUT =
  "w-full rounded-lg border border-line bg-background px-3.5 py-2.5 text-sm outline-none transition-colors placeholder:text-muted/60 focus:border-accent/70";
const BUTTON =
  "rounded-full border border-line px-4 py-2 font-subheading text-sm transition-colors hover:border-accent/60 disabled:opacity-50";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function SourceStatus({ source }: { source: Source }) {
  if (source.kind === "github") {
    return <span className="font-mono text-[11px] text-accent">connected</span>;
  }
  switch (source.status) {
    case "ready":
      return (
        <span className="font-mono text-[11px] text-accent">
          indexed · {source.chunk_count ?? 0} chunks
        </span>
      );
    case "failed":
      return (
        <span className="font-mono text-[11px] text-red-400" title={source.error ?? undefined}>
          failed{source.error ? `: ${source.error}` : ""}
        </span>
      );
    default:
      return <span className="font-mono text-[11px] text-amber-200">indexing…</span>;
  }
}

function CardError({ message }: { message: string }) {
  if (!message) return null;
  return (
    <p role="alert" className="mt-3 text-xs text-red-400">
      {message}
    </p>
  );
}

function UploadCard({
  kind,
  title,
  description,
  onAdded,
  onError,
}: {
  kind: "document" | "codebase";
  title: string;
  description: string;
  onAdded: (source: Source) => void;
  onError: (error: unknown) => string;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const { extensions, maxMb } = UPLOAD_LIMITS[kind];

  async function handleFiles(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = ""; // lets the same file be picked again after an error
    setError("");
    setBusy(true);
    for (const file of files) {
      const problem = validateUpload(kind, file);
      if (problem) {
        setError(`${file.name}: ${problem}`);
        continue;
      }
      try {
        onAdded(await uploadSource(kind, file));
      } catch (err) {
        setError(`${file.name}: ${onError(err)}`);
      }
    }
    setBusy(false);
  }

  return (
    <div className={CARD}>
      <h3 className="text-lg">{title}</h3>
      <p className="mt-1.5 flex-1 text-sm leading-relaxed text-muted">{description}</p>
      <p className="mt-3 font-mono text-[11px] text-muted">
        {extensions.join(" ")} · up to {maxMb} MB
      </p>
      <input
        ref={inputRef}
        type="file"
        accept={extensions.join(",")}
        multiple={kind === "document"}
        onChange={handleFiles}
        className="sr-only"
        aria-label={title}
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={busy}
        className={`${BUTTON} mt-4 self-start`}
      >
        {busy ? "Uploading…" : "Choose file"}
      </button>
      <CardError message={error} />
    </div>
  );
}

function GithubCard({
  onAdded,
  onError,
}: {
  onAdded: (source: Source) => void;
  onError: (error: unknown) => string;
}) {
  const [repository, setRepository] = useState("");
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const problem = validateRepository(repository) ?? validateGithubToken(token);
    setError(problem ?? "");
    if (problem) return;

    setBusy(true);
    try {
      onAdded(await connectGithub(repository.trim(), token));
      setRepository("");
      setToken("");
    } catch (err) {
      setError(onError(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className={CARD}>
      <h3 className="text-lg">Connect GitHub</h3>
      <p className="mt-1.5 text-sm leading-relaxed text-muted">
        Agents reach the repository through the GitHub MCP server. The token is checked against the
        repository and stored encrypted.
      </p>
      <label htmlFor="repository" className="sr-only">
        Repository
      </label>
      <input
        id="repository"
        value={repository}
        onChange={(e) => setRepository(e.target.value)}
        placeholder="owner/repository"
        autoComplete="off"
        spellCheck={false}
        className={`${INPUT} mt-4`}
      />
      <label htmlFor="github-token" className="sr-only">
        Personal access token
      </label>
      <input
        id="github-token"
        type="password"
        value={token}
        onChange={(e) => setToken(e.target.value)}
        placeholder="Personal access token (read access)"
        autoComplete="off"
        className={`${INPUT} mt-2.5`}
      />
      <button type="submit" disabled={busy} className={`${BUTTON} mt-4 self-start`}>
        {busy ? "Connecting…" : "Connect"}
      </button>
      <CardError message={error} />
    </form>
  );
}

export function SourcesPanel() {
  const router = useRouter();
  const [sources, setSources] = useState<Source[] | null>(null);
  const [listError, setListError] = useState("");

  // An expired session sends the user back to log in; anything else is shown inline.
  const describeError = useCallback(
    (error: unknown): string => {
      if (error instanceof ApiError && error.status === 401) router.replace("/login");
      return error instanceof Error ? error.message : "Something went wrong";
    },
    [router],
  );

  useEffect(() => {
    listSources()
      .then(setSources)
      .catch((error) => setListError(describeError(error)));
  }, [describeError]);

  // Uploads are indexed in the background, so keep refreshing until none are in progress.
  const indexing = sources?.some((s) => s.status === "pending" || s.status === "indexing");
  useEffect(() => {
    if (!indexing) return;
    const timer = setInterval(() => {
      listSources()
        .then(setSources)
        .catch(() => {});
    }, 2000);
    return () => clearInterval(timer);
  }, [indexing]);

  const addSource = (source: Source) => setSources((current) => [source, ...(current ?? [])]);

  async function handleReindex(id: string) {
    setListError("");
    try {
      const updated = await reindexSource(id);
      setSources((current) => current?.map((s) => (s.id === id ? updated : s)) ?? null);
    } catch (error) {
      setListError(describeError(error));
    }
  }

  async function handleRemove(id: string) {
    setListError("");
    try {
      await deleteSource(id);
      setSources((current) => current?.filter((source) => source.id !== id) ?? null);
    } catch (error) {
      setListError(describeError(error));
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-5 lg:grid-cols-3">
        <UploadCard
          kind="document"
          title="Upload documents"
          description="Technical docs, architecture notes and PDFs for the knowledge base."
          onAdded={addSource}
          onError={describeError}
        />
        <UploadCard
          kind="codebase"
          title="Upload a codebase"
          description="A zip archive of a project's source code."
          onAdded={addSource}
          onError={describeError}
        />
        <GithubCard onAdded={addSource} onError={describeError} />
      </div>

      <div className="rounded-2xl border border-line">
        <div className="flex items-baseline justify-between border-b border-line px-6 py-4">
          <h3 className="text-sm">Your sources</h3>
          <p className="text-xs text-muted">Uploads are searchable once indexed.</p>
        </div>
        {listError && (
          <p role="alert" className="px-6 py-4 text-sm text-red-400">
            {listError}
          </p>
        )}
        {sources === null && !listError && <p className="px-6 py-4 text-sm text-muted">Loading…</p>}
        {sources?.length === 0 && (
          <p className="px-6 py-4 text-sm text-muted">Nothing here yet. Add a source above.</p>
        )}
        {sources && sources.length > 0 && (
          <ul className="divide-y divide-line">
            {sources.map((source) => (
              <li key={source.id} className="flex items-center gap-4 px-6 py-3.5">
                <span className="w-20 shrink-0 font-mono text-[11px] text-accent">
                  {KIND_LABEL[source.kind]}
                </span>
                <span className="min-w-0 flex-1 truncate text-sm">{source.name}</span>
                <SourceStatus source={source} />
                {source.status === "failed" && (
                  <button
                    type="button"
                    onClick={() => handleReindex(source.id)}
                    className="text-xs text-muted hover:text-accent"
                  >
                    Retry
                  </button>
                )}
                {source.size_bytes !== null && (
                  <span className="font-mono text-xs text-muted">{formatSize(source.size_bytes)}</span>
                )}
                <button
                  type="button"
                  onClick={() => handleRemove(source.id)}
                  className="text-xs text-muted hover:text-red-400"
                  aria-label={`Remove ${source.name}`}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
