const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export async function downloadResultReportPdf(
  jobId: string,
  token: string
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/reports/jobs/${jobId}/pdf`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await response.blob();

  if (!response.ok) {
    throw new Error("Failed to download PDF report.");
  }

  const url = window.URL.createObjectURL(data);
  const link = document.createElement("a");

  link.href = url;
  link.download = `deepfake-analysis-report-${jobId}.pdf`;

  document.body.appendChild(link);
  link.click();
  link.remove();

  window.URL.revokeObjectURL(url);
}