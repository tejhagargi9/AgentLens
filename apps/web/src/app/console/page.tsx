import type { Metadata } from "next";

import { Logo } from "@/components/landing/logo";
import { LogoutButton } from "@/components/logout-button";
import { RunConsole } from "@/components/run-console";
import { SourcesPanel } from "@/components/sources-panel";
import { requireUser } from "@/lib/session";

export const metadata: Metadata = { title: "Console — AgentLens" };

export default async function ConsolePage() {
  const user = await requireUser();

  return (
    <>
      <header className="border-b border-line">
        <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between gap-4 px-6">
          <Logo />
          <div className="flex min-w-0 items-center gap-4">
            <span className="hidden truncate text-sm text-muted sm:block">{user.email}</span>
            <LogoutButton />
          </div>
        </div>
      </header>
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-14 px-6 py-12">
        <section className="flex flex-col gap-6">
          <div>
            <h1 className="text-4xl">Sources</h1>
            <p className="mt-2 text-sm text-muted">
              Add the documents and code you want AgentLens to work from.
            </p>
          </div>
          <SourcesPanel />
        </section>

        <section className="flex flex-col gap-6">
          <div>
            <h2 className="text-4xl">Ask</h2>
            <p className="mt-2 text-sm text-muted">
              Ask a question and follow each agent as it runs.
            </p>
          </div>
          <RunConsole />
        </section>
      </main>
    </>
  );
}
