"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  FileImage,
  RefreshCw,
  UploadCloud,
} from "lucide-react";

import { uploadMediaFile } from "@/lib/uploads";
import type { UploadResponse } from "@/types/upload";

const TOKEN_KEY = "deepfake_access_token";

function formatFileSize(bytes: number) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(2)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export default function UploadPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);

  const isImage = useMemo(() => {
    return selectedFile?.type.startsWith("image/") || false;
  }, [selectedFile]);

  const isVideo = useMemo(() => {
    return selectedFile?.type.startsWith("video/") || false;
  }, [selectedFile]);

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];

    setError("");
    setUploadResult(null);

    if (!file) {
      setSelectedFile(null);
      setPreviewUrl("");
      return;
    }

    setSelectedFile(file);

    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
  }

  async function handleUpload() {
    try {
      setError("");
      setUploadResult(null);

      if (!selectedFile) {
        throw new Error("Please select an image or video first.");
      }

      const token = localStorage.getItem(TOKEN_KEY);

      if (!token) {
        throw new Error("You are not logged in. Please login first.");
      }

      setUploading(true);

      const result = await uploadMediaFile(selectedFile, token);

      setUploadResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  function resetUpload() {
    setSelectedFile(null);
    setPreviewUrl("");
    setUploadResult(null);
    setError("");
  }

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-10 text-white">
      <div className="mx-auto max-w-5xl">
        <Link
          href="/dashboard"
          className="mb-6 inline-flex items-center gap-2 text-sm text-slate-300 hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </Link>

        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight md:text-4xl">
            Upload Media
          </h1>
          <p className="mt-2 text-slate-400">
            Upload an image or video to create an analysis job.
          </p>
        </div>

        <section className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
            <div className="flex items-center gap-3">
              <UploadCloud className="h-6 w-6 text-slate-300" />
              <h2 className="text-xl font-bold">Select File</h2>
            </div>

            <label className="mt-6 flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-slate-700 bg-slate-950/60 px-6 py-12 text-center hover:border-slate-500 hover:bg-slate-900">
              <FileImage className="h-12 w-12 text-slate-500" />
              <p className="mt-4 text-sm font-semibold text-slate-200">
                Click to choose image or video
              </p>
              <p className="mt-2 text-xs text-slate-500">
                Supported: JPG, PNG, WEBP, MP4, MOV, AVI
              </p>

              <input
                type="file"
                accept="image/jpeg,image/png,image/webp,video/mp4,video/quicktime,video/x-msvideo"
                onChange={handleFileChange}
                className="hidden"
              />
            </label>

            {selectedFile && (
              <div className="mt-6 rounded-xl border border-slate-800 bg-slate-950 p-5">
                <p className="text-sm text-slate-500">Selected File</p>
                <p className="mt-1 break-words font-semibold text-slate-200">
                  {selectedFile.name}
                </p>

                <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-slate-500">Type</p>
                    <p className="text-slate-300">{selectedFile.type}</p>
                  </div>

                  <div>
                    <p className="text-slate-500">Size</p>
                    <p className="text-slate-300">
                      {formatFileSize(selectedFile.size)}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {error && (
              <div className="mt-6 flex items-start gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-red-100">
                <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
                <p className="text-sm">{error}</p>
              </div>
            )}

            <div className="mt-6 flex flex-wrap gap-3">
              <button
                onClick={handleUpload}
                disabled={!selectedFile || uploading}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-bold text-slate-950 hover:bg-slate-200 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {uploading ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <UploadCloud className="h-4 w-4" />
                    Upload & Create Job
                  </>
                )}
              </button>

              <button
                onClick={resetUpload}
                disabled={uploading}
                className="rounded-xl border border-slate-700 px-5 py-3 text-sm font-bold text-slate-200 hover:bg-slate-900 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Reset
              </button>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
            <h2 className="text-xl font-bold">Preview</h2>

            <div className="mt-6 flex min-h-[320px] items-center justify-center overflow-hidden rounded-2xl border border-slate-800 bg-slate-950">
              {!previewUrl ? (
                <p className="text-sm text-slate-500">
                  Preview will appear here.
                </p>
              ) : isImage ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={previewUrl}
                  alt="Selected preview"
                  className="max-h-[420px] w-full object-contain"
                />
              ) : isVideo ? (
                <video
                  src={previewUrl}
                  controls
                  className="max-h-[420px] w-full"
                />
              ) : (
                <p className="text-sm text-slate-500">
                  Preview is not available for this file type.
                </p>
              )}
            </div>
          </div>
        </section>

        {uploadResult && (
          <section className="mt-6 rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-6">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="mt-1 h-6 w-6 shrink-0 text-emerald-300" />

              <div className="w-full">
                <h2 className="text-xl font-bold text-emerald-100">
                  Upload Successful
                </h2>

                <p className="mt-2 text-sm text-emerald-100/80">
                  Your file has been stored and an analysis job has been created.
                </p>

                <div className="mt-5 grid gap-4 text-sm md:grid-cols-2">
                  <div>
                    <p className="text-emerald-200/70">Upload ID</p>
                    <p className="mt-1 break-all text-emerald-50">
                      {uploadResult.upload_id}
                    </p>
                  </div>

                  <div>
                    <p className="text-emerald-200/70">Job ID</p>
                    <p className="mt-1 break-all text-emerald-50">
                      {uploadResult.job_id}
                    </p>
                  </div>

                  <div>
                    <p className="text-emerald-200/70">Upload Status</p>
                    <p className="mt-1 text-emerald-50">
                      {uploadResult.upload_status}
                    </p>
                  </div>

                  <div>
                    <p className="text-emerald-200/70">Analysis Status</p>
                    <p className="mt-1 text-emerald-50">
                      {uploadResult.analysis_status}
                    </p>
                  </div>
                </div>

                <div className="mt-6 flex flex-wrap gap-3">
                  <Link
                    href={`/result?job_id=${uploadResult.job_id}`}
                    className="rounded-xl bg-white px-5 py-3 text-sm font-bold text-slate-950 hover:bg-slate-200"
                  >
                    View Result
                  </Link>

                  <Link
                    href="/dashboard"
                    className="rounded-xl border border-emerald-400/40 px-5 py-3 text-sm font-bold text-emerald-50 hover:bg-emerald-500/10"
                  >
                    Go to Dashboard
                  </Link>
                </div>

                <div className="mt-5 rounded-xl border border-yellow-500/30 bg-yellow-500/10 p-4 text-sm text-yellow-100">
                  If the result page says the analysis result is not available
                  yet, run the worker:
                  <pre className="mt-3 overflow-x-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-100">
                    python -m app.workers.analysis_worker --once
                  </pre>
                  Then refresh the result page.
                </div>
              </div>
            </div>
          </section>
        )}
      </div>
    </main>
  );
}