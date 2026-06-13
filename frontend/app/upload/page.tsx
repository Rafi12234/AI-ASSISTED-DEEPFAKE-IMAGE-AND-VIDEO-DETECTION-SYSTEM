"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChangeEvent, useEffect, useMemo, useState } from "react";
import { FileVideo, ImageIcon, LogIn, UploadCloud } from "lucide-react";

import { clearAuth, getCurrentUser, getStoredToken } from "@/lib/auth";
import { uploadMediaFile } from "@/lib/uploads";
import type { UploadResponse } from "@/types/upload";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

const MAX_IMAGE_SIZE_MB = 20;
const MAX_VIDEO_SIZE_MB = 500;

const allowedTypes = [
  "image/jpeg",
  "image/png",
  "image/webp",
  "video/mp4",
  "video/quicktime",
  "video/x-msvideo",
];

function formatBytes(bytes: number) {
  const mb = bytes / (1024 * 1024);
  return `${mb.toFixed(2)} MB`;
}

export default function UploadPage() {
  const router = useRouter();

  const [checkingAuth, setCheckingAuth] = useState(true);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);

  useEffect(() => {
    async function checkAuth() {
      const token = getStoredToken();

      if (!token) {
        setIsLoggedIn(false);
        setCheckingAuth(false);
        return;
      }

      try {
        await getCurrentUser();
        setIsLoggedIn(true);
      } catch {
        clearAuth();
        setIsLoggedIn(false);
      } finally {
        setCheckingAuth(false);
      }
    }

    checkAuth();
  }, []);

  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl(null);
      return;
    }

    const url = URL.createObjectURL(selectedFile);
    setPreviewUrl(url);

    return () => {
      URL.revokeObjectURL(url);
    };
  }, [selectedFile]);

  const fileType = useMemo(() => {
    if (!selectedFile) return null;

    if (selectedFile.type.startsWith("image/")) return "image";
    if (selectedFile.type.startsWith("video/")) return "video";

    return "unknown";
  }, [selectedFile]);

  function validateFrontendFile(file: File) {
    if (!allowedTypes.includes(file.type)) {
      return "Unsupported file type. Please upload JPG, PNG, WEBP, MP4, MOV, or AVI.";
    }

    const sizeMb = file.size / (1024 * 1024);

    if (file.type.startsWith("image/") && sizeMb > MAX_IMAGE_SIZE_MB) {
      return `Image is too large. Maximum size is ${MAX_IMAGE_SIZE_MB}MB.`;
    }

    if (file.type.startsWith("video/") && sizeMb > MAX_VIDEO_SIZE_MB) {
      return `Video is too large. Maximum size is ${MAX_VIDEO_SIZE_MB}MB.`;
    }

    return "";
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setError("");
    setUploadResult(null);
    setProgress(0);

    const file = event.target.files?.[0];

    if (!file) {
      setSelectedFile(null);
      return;
    }

    const validationError = validateFrontendFile(file);

    if (validationError) {
      setSelectedFile(null);
      setError(validationError);
      return;
    }

    setSelectedFile(file);
  }

  async function handleUpload() {
    if (!selectedFile) {
      setError("Please select a file first.");
      return;
    }

    setError("");
    setUploading(true);
    setProgress(0);
    setUploadResult(null);

    try {
      const result = await uploadMediaFile(selectedFile, setProgress);
      setUploadResult(result);
      setProgress(100);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  if (checkingAuth) {
    return (
      <main className="min-h-screen bg-[#0D0F14] px-6 py-16 text-white">
        <div className="mx-auto max-w-4xl">
          <p className="text-zinc-400">Checking login status...</p>
        </div>
      </main>
    );
  }

  if (!isLoggedIn) {
    return (
      <main className="min-h-screen bg-[#0D0F14] px-6 py-16 text-white">
        <div className="mx-auto max-w-3xl">
          <Card className="border-white/10 bg-white/5 text-white">
            <CardContent className="p-8 text-center">
              <LogIn className="mx-auto mb-4 h-10 w-10" />
              <h1 className="text-2xl font-bold">Login Required</h1>
              <p className="mt-3 text-zinc-400">
                You need to login before uploading media for analysis.
              </p>

              <Button asChild className="mt-6">
                <Link href="/login">Go to Login</Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#0D0F14] px-6 py-16 text-white">
      <div className="mx-auto max-w-4xl">
        <div className="mb-10">
          <h1 className="text-3xl font-bold">Upload Media</h1>
          <p className="mt-3 text-zinc-400">
            Upload an image or video for AI-assisted deepfake analysis.
          </p>
        </div>

        {error && (
          <Alert className="mb-6 border-red-500/40 bg-red-500/10 text-red-200">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {uploadResult && (
          <Alert className="mb-6 border-emerald-500/40 bg-emerald-500/10 text-emerald-100">
            <AlertDescription>
              Upload successful. Analysis job has been created with status{" "}
              <strong>{uploadResult.analysis_status}</strong>.
            </AlertDescription>
          </Alert>
        )}

        <Card className="border-white/10 bg-white/5 text-white">
          <CardContent className="p-8">
            <label
              htmlFor="media-file"
              className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-white/20 bg-black/20 px-6 py-12 text-center transition hover:bg-white/5"
            >
              <UploadCloud className="mb-4 h-12 w-12 text-zinc-300" />
              <span className="text-lg font-semibold">
                Click to choose image or video
              </span>
              <span className="mt-2 text-sm text-zinc-400">
                Supported: JPG, PNG, WEBP, MP4, MOV, AVI
              </span>
              <span className="mt-1 text-xs text-zinc-500">
                Images up to 20MB, videos up to 500MB
              </span>
            </label>

            <input
              id="media-file"
              type="file"
              accept=".jpg,.jpeg,.png,.webp,.mp4,.mov,.avi,image/jpeg,image/png,image/webp,video/mp4,video/quicktime,video/x-msvideo"
              className="hidden"
              onChange={handleFileChange}
            />

            {selectedFile && (
              <div className="mt-8 grid gap-6 md:grid-cols-[220px_1fr]">
                <div className="overflow-hidden rounded-xl border border-white/10 bg-black/30">
                  {fileType === "image" && previewUrl && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={previewUrl}
                      alt="Selected file preview"
                      className="h-56 w-full object-cover"
                    />
                  )}

                  {fileType === "video" && previewUrl && (
                    <video
                      src={previewUrl}
                      controls
                      className="h-56 w-full object-cover"
                    />
                  )}

                  {fileType === "unknown" && (
                    <div className="flex h-56 items-center justify-center">
                      <UploadCloud className="h-12 w-12 text-zinc-400" />
                    </div>
                  )}
                </div>

                <div>
                  <div className="flex items-center gap-3">
                    {fileType === "image" ? (
                      <ImageIcon className="h-5 w-5" />
                    ) : (
                      <FileVideo className="h-5 w-5" />
                    )}

                    <h2 className="text-xl font-semibold">
                      {selectedFile.name}
                    </h2>
                  </div>

                  <div className="mt-4 flex flex-wrap gap-3">
                    <Badge variant="secondary">{fileType}</Badge>
                    <Badge variant="secondary">{selectedFile.type}</Badge>
                    <Badge variant="secondary">
                      {formatBytes(selectedFile.size)}
                    </Badge>
                  </div>

                  {uploading && (
                    <div className="mt-6">
                      <div className="mb-2 flex justify-between text-sm text-zinc-400">
                        <span>Uploading...</span>
                        <span>{progress}%</span>
                      </div>
                      <Progress value={progress} />
                    </div>
                  )}

                  {uploadResult && (
                    <div className="mt-6 rounded-xl border border-white/10 bg-black/20 p-4 text-sm text-zinc-300">
                      <p>
                        <strong>Upload ID:</strong> {uploadResult.upload_id}
                      </p>
                      <p className="mt-2">
                        <strong>Job ID:</strong> {uploadResult.job_id}
                      </p>
                      <p className="mt-2">
                        <strong>Status:</strong>{" "}
                        {uploadResult.analysis_status}
                      </p>
                    </div>
                  )}

                  <div className="mt-8 flex flex-wrap gap-3">
                    <Button
                      onClick={handleUpload}
                      disabled={uploading || !selectedFile}
                    >
                      {uploading ? "Uploading..." : "Upload for Analysis"}
                    </Button>

                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => router.push("/dashboard")}
                    >
                      View Dashboard
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </main>
  );
}