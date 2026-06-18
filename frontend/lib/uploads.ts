import type { MyUpload, UploadResponse } from "@/types/upload";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export async function uploadMediaFile(
  file: File,
  token: string
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/uploads`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(data?.detail || "Upload failed.");
  }

  return data as UploadResponse;
}

export async function getMyUploads(token: string): Promise<MyUpload[]> {
  const response = await fetch(`${API_BASE_URL}/api/uploads`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(data?.detail || "Failed to load uploads.");
  }

  if (Array.isArray(data)) {
    return data as MyUpload[];
  }

  if (Array.isArray(data?.items)) {
    return data.items as MyUpload[];
  }

  if (Array.isArray(data?.uploads)) {
    return data.uploads as MyUpload[];
  }

  return [];
}