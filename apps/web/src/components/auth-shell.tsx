import { Logo } from "@/components/landing/logo";

export function AuthShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <main className="relative flex flex-1 flex-col items-center overflow-hidden px-6 py-16">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute left-1/2 top-0 size-[50rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle,rgb(197_242_119/0.14),transparent_60%)]"
      />
      <div className="relative w-full max-w-md">
        <Logo />
        <h1 className="mt-10 text-5xl leading-none">{title}</h1>
        <p className="mt-3 text-muted">{subtitle}</p>
        <div className="mt-8 rounded-2xl border border-line bg-surface p-7">{children}</div>
      </div>
    </main>
  );
}
