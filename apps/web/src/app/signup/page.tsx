import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { AuthForm } from "@/components/auth-form";
import { AuthShell } from "@/components/auth-shell";
import { getCurrentUser } from "@/lib/session";

export const metadata: Metadata = { title: "Sign up — AgentLens" };

export default async function SignupPage() {
  if (await getCurrentUser()) redirect("/console");

  return (
    <AuthShell title="Create your account" subtitle="Sign up to add your sources and start asking.">
      <AuthForm mode="signup" />
    </AuthShell>
  );
}
