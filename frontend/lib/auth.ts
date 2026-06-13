import { apiFetch } from "@/lib/api";
import type { AuthResponse, AuthUser, MeResponse } from "@/types/auth";

const TOKEN_KEY = "deepfake_access_token";
const USER_KEY = "deepfake_user";

export function saveAuth(data: AuthResponse) {
  localStorage.setItem(TOKEN_KEY, data.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(data.user));
}

export function getStoredToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;

  const rawUser = localStorage.getItem(USER_KEY);

  if (!rawUser) return null;

  try {
    return JSON.parse(rawUser) as AuthUser;
  } catch {
    return null;
  }
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export async function registerUser(email: string, password: string) {
  const data = await apiFetch<AuthResponse>("/api/auth/register", {
    method: "POST",
    auth: false,
    body: JSON.stringify({
      email,
      password,
    }),
  });

  saveAuth(data);
  return data;
}

export async function loginUser(email: string, password: string) {
  const data = await apiFetch<AuthResponse>("/api/auth/login", {
    method: "POST",
    auth: false,
    body: JSON.stringify({
      email,
      password,
    }),
  });

  saveAuth(data);
  return data;
}

export async function getCurrentUser() {
  const data = await apiFetch<MeResponse>("/api/auth/me", {
    method: "GET",
  });

  localStorage.setItem(USER_KEY, JSON.stringify(data.user));

  return data.user;
}