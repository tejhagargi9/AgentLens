import Link from "next/link";

import { Logo } from "./logo";

const LINKS = [
  { href: "#how", label: "How it works" },
  { href: "#capabilities", label: "Capabilities" },
  { href: "#use-cases", label: "Use cases" },
];

const PRIMARY =
  "rounded-full bg-foreground px-4 py-2 font-subheading text-sm font-medium text-background transition-opacity hover:opacity-85";

export function SiteHeader({ signedIn }: { signedIn: boolean }) {
  return (
    <header className="sticky top-0 z-20 border-b border-line bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-6">
        <Logo />
        <nav aria-label="Main" className="hidden items-center gap-8 text-sm text-muted md:flex">
          {LINKS.map((link) => (
            <a key={link.href} href={link.href} className="transition-colors hover:text-foreground">
              {link.label}
            </a>
          ))}
        </nav>
        {signedIn ? (
          <Link href="/console" className={PRIMARY}>
            Open console
          </Link>
        ) : (
          <div className="flex items-center gap-4">
            <Link href="/login" className="font-subheading text-sm text-muted transition-colors hover:text-foreground">
              Log in
            </Link>
            <Link href="/signup" className={PRIMARY}>
              Sign up
            </Link>
          </div>
        )}
      </div>
    </header>
  );
}
