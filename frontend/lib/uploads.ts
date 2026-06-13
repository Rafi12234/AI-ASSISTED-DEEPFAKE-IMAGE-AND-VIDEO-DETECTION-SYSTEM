import axios from "axios";

import { getStoredToken } from "@/lib/auth";
import type { UploadListResponse, UploadResponse } from "@/types/upload";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

function getAuthHeaders() {
  const token = getStoredToken();

  if (!token) {
    throw new Error("You must login before uploading media.");
  }

  return {
    Authorization: `Bearer ${token}`,
  };
}

export async function uploadMediaFile(
  file: File,
  onProgress?: (progress: number) => void
) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await axios.post<UploadResponse>(
    `${API_BASE_URL}/api/uploads`,
    formData,
    {
      headers: {
        ...getAuthHeaders(),
      },
      onUploadProgress: (event) => {
        if (!event.total || !onProgress) return;

        const progress = Math.round((event.loaded * 100) / event.total);
        onProgress(progress);
      },
    }
  );

  return response.data;
}

export async function getMyUploads() {
  const response = await axios.get<UploadListResponse>(
    `${API_BASE_URL}/api/uploads`,
    {
      headers: {
        ...getAuthHeaders(),
      },
    }
  );

  return response.data.uploads;
}