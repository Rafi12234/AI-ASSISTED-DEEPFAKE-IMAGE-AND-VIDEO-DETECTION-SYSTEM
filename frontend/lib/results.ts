import type { AnalysisResultResponse } from "@/types/result";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

async function requestResult(
  endpoint: string,
  token: string
): Promise<AnalysisResultResponse> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(data?.detail || "Failed to fetch analysis result.");
  }

  return data as AnalysisResultResponse;
}

export async function getResultByJobId(
  jobId: string,
  token: string
): Promise<AnalysisResultResponse> {
  return requestResult(`/api/results/jobs/${jobId}`, token);
}

export async function getResultByUploadId(
  uploadId: string,
  token: string
): Promise<AnalysisResultResponse> {
  return requestResult(`/api/results/uploads/${uploadId}`, token);
}