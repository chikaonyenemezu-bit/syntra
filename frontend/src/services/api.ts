import type {
  AuditEvent, ChainCheck, FaultMode, Incident, Severity, Summary, System, Telemetry, User,
} from "../types";

const TOKEN_KEY = "syntra_token";

export const auth = {
  get token(): string | null {
    try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
  },
  set(token: string | null) {
    try {
      if (token) localStorage.setItem(TOKEN_KEY, token);
      else localStorage.removeItem(TOKEN_KEY);
    } catch { /* storage unavailable */ }
  },
};

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (auth.token) headers.set("Authorization", `Bearer ${auth.token}`);
  if (init.body && typeof init.body === "string") headers.set("Content-Type", "application/json");
  const res = await fetch(path, { ...init, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch { /* not JSON */ }
    if (res.status === 401) auth.set(null);
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  async login(username: string, password: string): Promise<void> {
    const form = new URLSearchParams({ username, password });
    const res = await fetch("/api/auth/login", { method: "POST", body: form });
    if (!res.ok) throw new ApiError(res.status, "Incorrect username or password");
    auth.set((await res.json()).access_token);
  },
  me: () => request<User>("/api/auth/me"),

  systems: () => request<System[]>("/api/systems"),
  telemetry: (code: string, limit = 30) => request<Telemetry[]>(`/api/systems/${code}/telemetry?limit=${limit}`),
  summary: () => request<Summary>("/api/monitoring/summary"),
  setFault: (code: string, mode: FaultMode) => post<System>(`/api/monitoring/simulators/${code}/fault`, { mode }),

  incidents: () => request<Incident[]>("/api/incidents"),
  createIncident: (body: { title: string; description: string; severity: Severity; system_code: string | null }) =>
    post<Incident>("/api/incidents", body),
  acknowledge: (n: string) => post<Incident>(`/api/incidents/${n}/acknowledge`),
  resolve: (n: string, note: string) => post<Incident>(`/api/incidents/${n}/resolve`, { note }),
  close: (n: string) => post<Incident>(`/api/incidents/${n}/close`),

  audit: (params: Record<string, string> = {}) =>
    request<AuditEvent[]>(`/api/audit?${new URLSearchParams(params)}`),
  verifyAudit: () => request<ChainCheck>("/api/audit/verify"),
};
