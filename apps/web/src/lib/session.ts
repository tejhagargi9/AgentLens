// Server-side session helpers (Server Components only — uses next/headers).
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { API_URL } from "./api";
import type { User } from "./types";

// Set by the API on login; must match SESSION_COOKIE in apps/api/src/agentos/core/security.py.
const SESSION_COOKIE = "agentlens_session";

/** Cheap check used to pick which buttons to show. Not proof the session is still valid. */
export async function hasSessionCookie(): Promise<boolean> {
  return (await cookies()).has(SESSION_COOKIE);
}

/** Asks the API who the session cookie belongs to; null if signed out or expired. */
export async function getCurrentUser(): Promise<User | null> {
  const cookie = (await cookies()).get(SESSION_COOKIE);
  if (!cookie) return null;
  try {
    const response = await fetch(`${API_URL}/api/v1/auth/me`, {
      headers: { cookie: `${SESSION_COOKIE}=${cookie.value}` },
      cache: "no-store",
    });
    return response.ok ? ((await response.json()) as User) : null;
  } catch {
    return null;
  }
}

/** For pages that need a signed-in user: sends everyone else to the login page. */
export async function requireUser(): Promise<User> {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  return user;
}
