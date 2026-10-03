import Link from "next/link";

import { AGENTS } from "@/lib/types";

// Illustrative content for the product preview; not real output.
const EXAMPLE_CLAIMS = [
  { text: "Tokens are issued in the login handler", source: "src/auth/login.ts:42" },
  { text: "Every /api route passes through verifyJwt", source: "src/middleware/auth.ts:17" },
  { text: "Refresh tokens rotate on each use", source: "docs/security.md §3" },
];

function ExampleRun() {
  return (
    <figure className="overflow-hidden rounded-2xl border border-line bg-surface shadow-2xl shadow-black/50">
      <div className="flex items-center gap-2 border-b border-line px-4 py-3">
        <span className="size-2.5 rounded-full bg-foreground/15" />
        <span className="size-2.5 rounded-full bg-foreground/15" />
        <span className="size-2.5 rounded-full bg-foreground/15" />
        <figcaption className="ml-2 font-mono text-xs text-muted">Example run</figcaption>
      </div>

      <div className="grid md:grid-cols-[15rem_1fr]">
        <ol className="flex flex-col gap-2.5 border-b border-line p-5 font-mono text-xs md:border-r md:border-b-0">
          {AGENTS.map((agent, i) => (
            <li
              key={agent.id}
              className="trace-step flex items-center gap-2.5"
              style={{ "--i": i } as React.CSSProperties}
            >
              <span className="text-accent">✓</span>
              {agent.label}
            </li>
          ))}
        </ol>

        <div className="flex flex-col gap-4 p-5">
          <p className="font-mono text-xs text-muted">
            <span className="text-accent">›</span> How does authentication work in this repo?
          </p>
          <ul className="flex flex-col gap-3">
            {EXAMPLE_CLAIMS.map((claim, i) => (
              <li
                key={claim.source}
                className="trace-step rounded-lg border border-line p-3"
                style={{ "--i": AGENTS.length + i } as React.CSSProperties}
              >
                <p className="text-sm">{claim.text}</p>
                <p className="mt-1.5 flex flex-wrap items-center gap-2 font-mono text-[11px] text-muted">
                  <span className="rounded-full bg-accent/15 px-2 py-0.5 text-accent">verified</span>
                  {claim.source}
                </p>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </figure>
  );
}

export function Hero({ signedIn }: { signedIn: boolean }) {
  return (
    <section className="relative overflow-hidden">
      {/* Lens: soft glow plus concentric rings behind the headline. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute left-1/2 top-0 size-[70rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle,rgb(197_242_119/0.16),transparent_60%)]"
      />
      <svg
        aria-hidden="true"
        viewBox="0 0 800 800"
        className="pointer-events-none absolute left-1/2 top-0 size-[60rem] -translate-x-1/2 -translate-y-1/2 text-foreground/[0.07]"
        fill="none"
        stroke="currentColor"
      >
        <circle cx="400" cy="400" r="160" />
        <circle cx="400" cy="400" r="260" />
        <circle cx="400" cy="400" r="360" />
      </svg>

      <div className="relative mx-auto flex w-full max-w-6xl flex-col items-center px-6 pt-24 pb-20 text-center md:pt-32">
        <p className="rounded-full border border-line px-3.5 py-1.5 font-mono text-xs text-muted">
          Multi-agent research for codebases &amp; docs
        </p>
        <h1 className="mt-8 max-w-4xl text-6xl leading-[0.95] text-balance md:text-8xl">
          See how every answer was <em className="text-accent">reached</em>.
        </h1>
        <p className="mt-7 max-w-2xl text-lg leading-relaxed text-muted text-pretty">
          AgentLens breaks your question into a plan, searches your repositories and documentation,
          checks each claim against its source, and hands you a report you can trace line by line.
        </p>
        <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
          <Link
            href={signedIn ? "/console" : "/signup"}
            className="rounded-full bg-accent px-6 py-3 font-subheading text-sm font-medium text-background transition-opacity hover:opacity-85"
          >
            {signedIn ? "Open the console" : "Get started"}
          </Link>
          <a
            href="#how"
            className="rounded-full border border-line px-6 py-3 font-subheading text-sm font-medium transition-colors hover:border-foreground/40"
          >
            How it works
          </a>
        </div>

        <div className="mt-20 w-full max-w-4xl text-left">
          <ExampleRun />
        </div>
      </div>
    </section>
  );
}
