import type { AdminJobItem, AdminOverview } from "@/types/admin";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export type AdminJobFilters = {
  search?: string;
  jobStatus?: string;
  riskLevel?: string;
  mediaType?: string;
  limit?: number;
};

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

export async function getAdminJobs(
  token: string,
  filters: AdminJobFilters = {}
): Promise<AdminJobItem[]> {
  const params = new URLSearchParams();

  if (filters.search?.trim()) {
    params.set("search", filters.search.trim());
  }

  if (filters.jobStatus && filters.jobStatus !== "all") {
    params.set("job_status", filters.jobStatus);
  }

  if (filters.riskLevel && filters.riskLevel !== "all") {
    params.set("risk_level", filters.riskLevel);
  }

  if (filters.mediaType && filters.mediaType !== "all") {
    params.set("media_type", filters.mediaType);
  }

  if (filters.limit) {
    params.set("limit", String(filters.limit));
  }

  const query = params.toString();
  const endpoint = query ? `/api/admin/jobs?${query}` : "/api/admin/jobs";

  const result = await adminRequest<AdminJobItem[] | null>(endpoint, token);

  if (!Array.isArray(result)) {
    return [];
  }

  return result;
}