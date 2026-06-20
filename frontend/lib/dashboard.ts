import type { DashboardJobItem } from "@/types/dashboard";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export type DashboardJobFilters = {
  search?: string;
  jobStatus?: string;
  riskLevel?: string;
  mediaType?: string;
  limit?: number;
};

export async function getDashboardJobs(
  token: string,
  filters: DashboardJobFilters = {}
): Promise<DashboardJobItem[]> {
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
  const endpoint = query ? `/api/dashboard/jobs?${query}` : "/api/dashboard/jobs";

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(data?.detail || "Failed to load dashboard jobs.");
  }

  if (!Array.isArray(data)) {
    return [];
  }

  return data as DashboardJobItem[];
}