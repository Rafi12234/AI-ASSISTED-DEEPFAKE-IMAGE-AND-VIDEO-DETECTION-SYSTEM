import type { AdminJobItem, AdminOverview } from "@/types/admin";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

async function adminRequest<T>(endpoint: string, token: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(data?.detail || "Admin request failed.");
  }

  return data as T;
}

export async function getAdminOverview(token: string): Promise<AdminOverview> {
  return adminRequest<AdminOverview>("/api/admin/overview", token);
}

export async function getAdminJobs(token: string): Promise<AdminJobItem[]> {
  return adminRequest<AdminJobItem[]>("/api/admin/jobs", token);
}