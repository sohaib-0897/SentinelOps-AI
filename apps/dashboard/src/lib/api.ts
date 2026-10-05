export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {super(message);}
}

export async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers: body === undefined ? undefined : {"Content-Type": "application/json"},
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new ApiError(typeof error?.detail === "string" ? error.detail : `Request failed (${response.status})`, response.status);
  }
  return response.json() as Promise<T>;
}

export function percent(value: number): string {return `${(value * 100).toFixed(value < .01 ? 1 : 0)}%`;}
export function clockTime(value: string): string {return new Date(value).toLocaleTimeString([], {hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit"});}
export function label(value: string): string {return value.replaceAll("_", " ").replaceAll("-", " ").toLowerCase();}
export function isActive(state: string): boolean {return !["RESOLVED", "CLOSED", "FAILED"].includes(state);}
