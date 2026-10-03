import Link from "next/link";

import { Logo } from "./logo";

const STEPS = [
  { name: "Plan", body: "The planner reads your request and splits it into tasks the other agents can execute." },
  { name: "Retrieve", body: "Hybrid search — semantic and keyword, fused and reranked — pulls the passages that matter from your knowledge base." },
  { name: "Inspect", body: "The GitHub agent explores the repository through MCP tools: files, code search, commits, issues and pull requests." },
  { name: "Analyse", body: "Relevant source files are read and connected, then combined with the retrieved context into findings." },
  { name: "Verify", body: "Every claim is checked against its evidence. Anything unsupported is marked as needing review, not passed off as fact." },
  { name: "Report", body: "You get a structured technical report with source references and a summary of what each agent did." },
];

const CAPABILITIES = [
  { name: "Hybrid RAG", body: "Vector search, BM25, reciprocal rank fusion and reranking over docs, PDFs, Markdown and source code." },
  { name: "Multi-agent workflow", body: "Specialised agents share one workflow state, so each builds on the work of the last instead of starting over." },
  { name: "GitHub via MCP", body: "Repository access through the Model Context Protocol, alongside custom tools for knowledge and code analysis." },
  { name: "Evidence-first answers", body: "Findings carry citations to files and documents. If something can't be verified, the report says so." },
  { name: "Human approval", body: "Write operations such as opening an issue pause for your sign-off before any tool is executed." },
  { name: "Evaluation & tracing", body: "Faithfulness, relevancy, latency, token cost and tool success are measured rather than assumed." },
];

const USE_CASES = [
  { label: "Architecture", question: "How do the frontend, backend, database and APIs in this repository fit together?" },
  { label: "Authentication", question: "Which files handle login, token generation and authorization?" },
  { label: "Docs vs. code", question: "Where does the API documentation disagree with the implementation?" },
  { label: "Bug investigation", question: "Given these logs, which code paths could be causing the failure?" },
  { label: "Feature tracing", question: "How does a payment travel from the frontend request to the database?" },
];

function SectionHeading({ eyebrow, title, intro }: { eyebrow: string; title: string; intro: string }) {
  return (
    <div className="max-w-2xl">
      <p className="font-mono text-xs uppercase tracking-widest text-accent">{eyebrow}</p>
      <h2 className="mt-4 text-4xl leading-tight text-balance md:text-5xl">{title}</h2>
      <p className="mt-5 text-lg leading-relaxed text-muted text-pretty">{intro}</p>
    </div>
  );
}

export function HowItWorks() {
  return (
    <section id="how" className="scroll-mt-16 border-t border-line">
      <div className="mx-auto w-full max-w-6xl px-6 py-24">
        <SectionHeading
          eyebrow="How it works"
          title="Planned, executed, verified — then written."
          intro="A single model call guesses. AgentLens runs your question through a pipeline of specialised agents, and shows you each step as it happens."
        />
        <ol className="mt-14 grid gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
          {STEPS.map((step, i) => (
            <li key={step.name} className="bg-background p-7">
              <p className="font-mono text-xs text-muted">{String(i + 1).padStart(2, "0")}</p>
              <h3 className="mt-4 text-xl">{step.name}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{step.body}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

export function Capabilities() {
  return (
    <section id="capabilities" className="scroll-mt-16 border-t border-line bg-surface">
      <div className="mx-auto w-full max-w-6xl px-6 py-24">
        <SectionHeading
          eyebrow="Capabilities"
          title="Built like a system, not a chatbot."
          intro="Retrieval, tools, orchestration and evaluation working together — with the workflow visible instead of hidden behind a reply."
        />
        <ul className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {CAPABILITIES.map((capability) => (
            <li
              key={capability.name}
              className="rounded-2xl border border-line bg-background p-7 transition-colors hover:border-accent/40"
            >
              <span aria-hidden="true" className="block size-2 rounded-full bg-accent" />
              <h3 className="mt-5 text-lg">{capability.name}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{capability.body}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

export function UseCases() {
  return (
    <section id="use-cases" className="scroll-mt-16 border-t border-line">
      <div className="mx-auto w-full max-w-6xl px-6 py-24">
        <SectionHeading
          eyebrow="Use cases"
          title="Questions it's made for."
          intro="The kind that normally mean an afternoon of searching through source files, docs, issues and commits."
        />
        <ul className="mt-14 divide-y divide-line border-y border-line">
          {USE_CASES.map((useCase) => (
            <li key={useCase.label} className="grid gap-2 py-7 md:grid-cols-[14rem_1fr] md:items-baseline">
              <h3 className="text-sm text-muted">{useCase.label}</h3>
              <p className="font-heading text-2xl leading-snug italic md:text-3xl">
                “{useCase.question}”
              </p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

export function CallToAction() {
  return (
    <section className="border-t border-line">
      <div className="mx-auto flex w-full max-w-6xl flex-col items-center px-6 py-28 text-center">
        <h2 className="max-w-3xl text-5xl leading-none text-balance md:text-7xl">
          Ask a question. <em className="text-accent">Watch</em> it get answered.
        </h2>
        <p className="mt-6 max-w-xl text-lg leading-relaxed text-muted">
          Open the console, type what you want to know, and follow each agent as it works.
        </p>
        <Link
          href="/console"
          className="mt-10 rounded-full bg-accent px-7 py-3.5 font-subheading text-sm font-medium text-background transition-opacity hover:opacity-85"
        >
          Open the console
        </Link>
      </div>
    </section>
  );
}

export function SiteFooter() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-8 text-sm text-muted">
        <Logo />
        <p>© {new Date().getFullYear()} AgentLens</p>
      </div>
    </footer>
  );
}
