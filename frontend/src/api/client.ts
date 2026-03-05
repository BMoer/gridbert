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
    // Auto-logout on 401 (expired/invalid token)
    if (res.status === 401) {
      localStorage.removeItem("gridbert_token");
      window.location.href = "/login";
      throw new ApiError(401, "Session abgelaufen");
    }
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

// --- User Files & Memory (for DocumentTable) ---

export interface UserFile {
  id: number;
  file_name: string;
  media_type: string;
  size_bytes: number;
  created_at: string;
}

export interface MemoryFact {
  id: number;
  fact_key: string;
  fact_value: string;
}

// --- News ---

export interface NewsItem {
  titel: string;
  zusammenfassung: string;
  quelle: string;
  url: string;
  datum: string | null;
  kategorie: string;
}

export function getEnergyNews() {
  return apiFetch<NewsItem[]>("/news");
}

export function getUserFiles() {
  return apiFetch<UserFile[]>("/files");
}

export function getUserMemory() {
  return apiFetch<MemoryFact[]>("/memory");
}

// --- Settings (LLM Provider) ---

export interface SetupStatus {
  has_user_key: boolean;
  has_server_key: boolean;
  needs_setup: boolean;
  provider: string;
}

export interface LLMConfig {
  provider: string;
  model: string;
  has_key: boolean;
}

export interface LLMConfigInput {
  provider: string;
  api_key: string;
  model: string;
}

export function getSetupStatus() {
  return apiFetch<SetupStatus>("/settings/status");
}

export function getLLMConfig() {
  return apiFetch<LLMConfig>("/settings/llm");
}

export function setLLMConfig(config: LLMConfigInput) {
  return apiFetch<{ status: string }>("/settings/llm", {
    method: "PUT",
    body: JSON.stringify(config),
  });
}

export function deleteLLMConfig() {
  return apiFetch<void>("/settings/llm", { method: "DELETE" });
}
