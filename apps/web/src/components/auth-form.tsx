"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { login, signup } from "@/lib/api";
import { PASSWORD_MAX_LENGTH, PASSWORD_RULES, validateEmail, validateNewPassword } from "@/lib/validation";

type Mode = "login" | "signup";
type Errors = { email?: string; password?: string; confirm?: string; form?: string };

const INPUT =
  "w-full rounded-lg border border-line bg-background px-3.5 py-2.5 text-sm outline-none transition-colors placeholder:text-muted/60 focus:border-accent/70 aria-invalid:border-red-400/70";

function FieldError({ id, message }: { id: string; message?: string }) {
  if (!message) return null;
  return (
    <p id={id} role="alert" className="mt-1.5 text-xs text-red-400">
      {message}
    </p>
  );
}

export function AuthForm({ mode }: { mode: Mode }) {
  const router = useRouter();
  const isSignup = mode === "signup";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState<Errors>({});
  const [submitting, setSubmitting] = useState(false);

  function validate(): Errors {
    const next: Errors = {};
    const emailError = validateEmail(email);
    if (emailError) next.email = emailError;

    if (isSignup) {
      const passwordError = validateNewPassword(password);
      if (passwordError) next.password = passwordError;
      if (!next.password && confirm !== password) next.confirm = "Passwords don't match";
    } else if (!password) {
      next.password = "Enter your password";
    }
    return next;
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const found = validate();
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setSubmitting(true);
    try {
      await (isSignup ? signup : login)(email.trim(), password);
      router.replace("/console");
      router.refresh();
    } catch (error) {
      setErrors({ form: error instanceof Error ? error.message : "Something went wrong" });
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-5">
      <div>
        <label htmlFor="email" className="mb-1.5 block font-subheading text-sm">
          Email
        </label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          onBlur={() => email && setErrors((prev) => ({ ...prev, email: validateEmail(email) ?? undefined }))}
          aria-invalid={Boolean(errors.email)}
          aria-describedby="email-error"
          placeholder="you@example.com"
          className={INPUT}
        />
        <FieldError id="email-error" message={errors.email} />
      </div>

      <div>
        <div className="mb-1.5 flex items-baseline justify-between">
          <label htmlFor="password" className="font-subheading text-sm">
            Password
          </label>
          <button
            type="button"
            onClick={() => setShowPassword((shown) => !shown)}
            aria-pressed={showPassword}
            className="text-xs text-muted hover:text-foreground"
          >
            {showPassword ? "Hide" : "Show"}
          </button>
        </div>
        <input
          id="password"
          type={showPassword ? "text" : "password"}
          autoComplete={isSignup ? "new-password" : "current-password"}
          maxLength={PASSWORD_MAX_LENGTH}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          aria-invalid={Boolean(errors.password)}
          aria-describedby={isSignup ? "password-rules password-error" : "password-error"}
          className={INPUT}
        />
        <FieldError id="password-error" message={errors.password} />

        {isSignup && (
          <ul id="password-rules" className="mt-3 grid gap-1.5 text-xs sm:grid-cols-2">
            {PASSWORD_RULES.map((rule) => {
              const met = rule.regex.test(password);
              return (
                <li key={rule.label} className={met ? "text-accent" : "text-muted"}>
                  <span aria-hidden="true">{met ? "✓" : "○"}</span> {rule.label}
                  <span className="sr-only">{met ? " (met)" : " (not met)"}</span>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {isSignup && (
        <div>
          <label htmlFor="confirm" className="mb-1.5 block font-subheading text-sm">
            Confirm password
          </label>
          <input
            id="confirm"
            type={showPassword ? "text" : "password"}
            autoComplete="new-password"
            maxLength={PASSWORD_MAX_LENGTH}
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            aria-invalid={Boolean(errors.confirm)}
            aria-describedby="confirm-error"
            className={INPUT}
          />
          <FieldError id="confirm-error" message={errors.confirm} />
        </div>
      )}

      {errors.form && (
        <p role="alert" className="rounded-lg border border-red-400/40 bg-red-400/10 px-3.5 py-2.5 text-sm text-red-300">
          {errors.form}
        </p>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="rounded-full bg-accent px-6 py-3 font-subheading text-sm font-medium text-background transition-opacity hover:opacity-85 disabled:opacity-50"
      >
        {submitting ? "Please wait…" : isSignup ? "Create account" : "Log in"}
      </button>

      <p className="text-center text-sm text-muted">
        {isSignup ? "Already have an account? " : "New to AgentLens? "}
        <Link href={isSignup ? "/login" : "/signup"} className="text-foreground underline underline-offset-4 hover:text-accent">
          {isSignup ? "Log in" : "Create an account"}
        </Link>
      </p>
    </form>
  );
}
