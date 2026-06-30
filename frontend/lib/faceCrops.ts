const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export function getFaceCropPreviewUrl(
  resultId: string,
  faceId: string
) {
  return `${API_BASE_URL}/api/face-crops/results/${resultId}/${faceId}/preview`;
}

export async function getFaceCropPreviewBlobUrl(
  resultId: string,
  faceId: string,
  token: string
): Promise<string> {
  const response = await fetch(
    getFaceCropPreviewUrl(resultId, faceId),
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      cache: "no-store",
    }
  );

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(data?.detail || "Failed to load face crop preview.");
  }

  const blob = await response.blob();

  return URL.createObjectURL(blob);
}