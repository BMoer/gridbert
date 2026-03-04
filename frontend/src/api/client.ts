/** API client for Gridbert backend. */

const BASE = "/api";

/** Get stored JWT token. */
function getToken(): string | null {
  return localStorage.getItem("gridbert_token");
}

/** Make an authenticated JSON request. */
export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || "Request failed");
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

// --- Auth ---

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  name: string;
}

export interface UserProfile {
  id: number;
  email: string;
  name: string;
  plz: string;
}

export function register(email: string, password: string, name: string) {
  return apiFetch<TokenResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, name }),
  });
}

export function login(email: string, password: string) {
  return apiFetch<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function getProfile() {
  return apiFetch<UserProfile>("/auth/me");
}

// --- Chat ---

export interface Conversation {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: number;
  conversation_id: number;
  role: string;
  content: string;
  tool_name: string | null;
  created_at: string;
}

export function getConversations() {
  return apiFetch<Conversation[]>("/conversations");
}

export function getMessages(conversationId: number) {
  return apiFetch<Message[]>(`/conversations/${conversationId}/messages`);
}

// --- Dashboard ---

export interface Widget {
  id: number;
  widget_type: string;
  position: number;
  config: Record<string, unknown>;
}

export function getWidgets() {
  return apiFetch<Widget[]>("/dashboard/widgets");
}

export function addWidget(widgetType: string, config: Record<string, unknown> = {}) {
  return apiFetch<Widget>("/dashboard/widgets", {
    method: "POST",
    body: JSON.stringify({ widget_type: widgetType, config }),
  });
}

export function deleteWidget(widgetId: number) {
  return apiFetch<void>(`/dashboard/widgets/${widgetId}`, { method: "DELETE" });
}
