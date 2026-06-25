import type { ProductionEvidenceResponse } from "@/types/aiModels";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export async function getResultProductionEvidence(
  resultId: string,
  token: string
): Promise<ProductionEvidenceResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/ai-models/results/${resultId}/evidence`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      cache: "no-store",
    }
  );

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(data?.detail || "Failed to load production evidence.");
  }

  return data as ProductionEvidenceResponse;
}