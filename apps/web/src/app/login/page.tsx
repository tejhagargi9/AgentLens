import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { AuthForm } from "@/components/auth-form";
import { AuthShell } from "@/components/auth-shell";
import { getCurrentUser } from "@/lib/session";

export const metadata: Metadata = { title: "Log in — AgentLens" };

export default async function LoginPage() {
  if (await getCurrentUser()) redirect("/console");

  return (
    <AuthShell title="Welcome back" subtitle="Log in to open your console.">
      <AuthForm mode="login" />
    </AuthShell>
  );
}
