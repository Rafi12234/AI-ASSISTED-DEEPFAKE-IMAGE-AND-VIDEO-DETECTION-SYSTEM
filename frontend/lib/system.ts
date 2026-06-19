import type { SystemHealthResponse } from "@/types/system";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export async function getSystemHealth(): Promise<SystemHealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/system/health`, {
    method: "GET",
    cache: "no-store",
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(data?.detail || "Failed to load system health.");
  }

  return data as SystemHealthResponse;
}