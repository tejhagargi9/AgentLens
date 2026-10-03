import Link from "next/link";

export function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2.5">
      <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
        <circle cx="11" cy="11" r="10" stroke="currentColor" strokeOpacity="0.35" strokeWidth="1.5" />
        <circle cx="11" cy="11" r="5.5" stroke="var(--accent)" strokeWidth="1.5" />
        <circle cx="11" cy="11" r="1.75" fill="var(--accent)" />
      </svg>
      <span className="font-subheading text-lg font-medium tracking-tight">AgentLens</span>
    </Link>
  );
}
