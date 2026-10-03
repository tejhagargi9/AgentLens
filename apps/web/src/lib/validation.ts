// Client-side checks for fast feedback. The API enforces the same rules
// (apps/api/src/agentos/core/security.py and api/routes/sources.py); change both together.

export const EMAIL_REGEX = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$/;

export const PASSWORD_RULES = [
  { label: "At least 8 characters", regex: /[\s\S]{8,}/ },
  { label: "A lowercase letter", regex: /[a-z]/ },
  { label: "An uppercase letter", regex: /[A-Z]/ },
  { label: "A number", regex: /\d/ },
  { label: "A special character", regex: /[^A-Za-z0-9]/ },
] as const;

export const PASSWORD_MAX_LENGTH = 128;

export function validateEmail(email: string): string | null {
  if (!email.trim()) return "Enter your email address";
  if (email.length > 320 || !EMAIL_REGEX.test(email.trim())) return "Enter a valid email address";
  return null;
}

export function validateNewPassword(password: string): string | null {
  if (!password) return "Choose a password";
  if (password.length > PASSWORD_MAX_LENGTH) return `Use at most ${PASSWORD_MAX_LENGTH} characters`;
  if (PASSWORD_RULES.some((rule) => !rule.regex.test(password))) {
    return "Password doesn't meet all the requirements";
  }
  return null;
}

// owner/name, or a github.com URL to the repository.
export const REPOSITORY_REGEX =
  /^(?:https?:\/\/github\.com\/)?[A-Za-z0-9][A-Za-z0-9-]{0,38}\/[A-Za-z0-9._-]{1,100}\/?$/;

export function validateRepository(repository: string): string | null {
  if (!REPOSITORY_REGEX.test(repository.trim())) {
    return "Enter a repository as owner/name or a github.com URL";
  }
  return null;
}

export function validateGithubToken(token: string): string | null {
  if (token.length < 20 || /\s/.test(token)) return "Enter a valid GitHub access token";
  return null;
}

const MB = 1024 * 1024;

export const UPLOAD_LIMITS = {
  document: { extensions: [".pdf", ".md", ".markdown", ".txt", ".rst"], maxMb: 25 },
  codebase: { extensions: [".zip"], maxMb: 100 },
} as const;

export function validateUpload(kind: keyof typeof UPLOAD_LIMITS, file: File): string | null {
  const { extensions, maxMb } = UPLOAD_LIMITS[kind];
  const name = file.name.toLowerCase();
  if (!extensions.some((extension) => name.endsWith(extension))) {
    return kind === "codebase"
      ? "A codebase must be uploaded as a .zip file"
      : `Documents must be one of: ${extensions.join(", ")}`;
  }
  if (file.size === 0) return "File is empty";
  if (file.size > maxMb * MB) return `File is larger than the ${maxMb} MB limit`;
  return null;
}
