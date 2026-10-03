"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { logout } from "@/lib/api";

export function LogoutButton() {
  const router = useRouter();
  const [pending, setPending] = useState(false);

  async function handleClick() {
    setPending(true);
    try {
      await logout();
    } finally {
      router.replace("/");
      router.refresh();
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={pending}
      className="rounded-full border border-line px-4 py-2 font-subheading text-sm transition-colors hover:border-foreground/40 disabled:opacity-50"
    >
      Log out
    </button>
  );
}
