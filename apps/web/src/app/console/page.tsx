import type { Metadata } from "next";

import { Logo } from "@/components/landing/logo";
import { RunConsole } from "@/components/run-console";

export const metadata: Metadata = { title: "Console — AgentLens" };

export default function ConsolePage() {
  return (
    <>
      <header className="border-b border-line">
        <div className="mx-auto flex h-16 w-full max-w-4xl items-center px-6">
          <Logo />
        </div>
      </header>
      <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-8 px-6 py-12">
        <div>
          <h1 className="text-4xl">Console</h1>
          <p className="mt-2 text-sm text-muted">
            Ask about a repository or your documentation and follow each agent as it runs.
          </p>
        </div>
        <RunConsole />
      </main>
    </>
  );
}
