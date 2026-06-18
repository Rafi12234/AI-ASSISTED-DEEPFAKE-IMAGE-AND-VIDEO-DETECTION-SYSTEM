"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  AlertCircle,
  BarChart3,
  Clock3,
  FileImage,
  LogIn,
  RefreshCw,
  ShieldCheck,
  Upload,
} from "lucide-react";

import { getMyUploads } from "@/lib/uploads";
import type { MyUpload } from "@/types/upload";

const TOKEN_KEY = "deepfake_access_token";
const USER_KEY = "deepfake_user";

type StoredUser = {
  id?: string;
  email?: string;
  role?: string;
};

function formatDate(value: string | null | undefined) {
  if (!value) {
    return "N/A";
  }

  return new Date(value).toLocaleString();
}

function formatFileSize(bytes: number | null | undefined) {
  if (!bytes) {
    return "N/A";
  }

  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(2)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function getUploadId(upload: MyUpload) {
  return upload.upload_id || upload.id || "";
}

function getStatusStyle(status?: string | null) {
  switch (status) {
    case "completed":
      return "border-emerald-500/40 bg-emerald-500/10 text-emerald-300";

    case "processing":
      return "border-blue-500/40 bg-blue-500/10 text-blue-300";

    case "queued":
      return "border-yellow-500/40 bg-yellow-500/10 text-yellow-300";

    case "failed":
      return "border-red-500/40 bg-red-500/10 text-red-300";

    case "stored":
      return "border-emerald-500/40 bg-emerald-500/10 text-emerald-300";

    default:
      return "border-slate-500/40 bg-slate-500/10 text-slate-300";
  }
}

export default function DashboardPage() {
  const [user, setUser] = useState<StoredUser | null>(null);
  const [uploads, setUploads] = useState<MyUpload[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  async function loadDashboard(isRefresh = false) {
    try {
      setError("");

      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      const token = localStorage.getItem(TOKEN_KEY);
      const userText = localStorage.getItem(USER_KEY);

      if (!token) {
        throw new Error("You are not logged in. Please login first.");
      }

      if (userText) {
        setUser(JSON.parse(userText) as StoredUser);
      }

      const uploadItems = await getMyUploads(token);
      setUploads(uploadItems);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      loadDashboard();
    }, 0);

    return () => {
      window.clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-950 px-6 py-10 text-white">
        <div className="mx-auto max-w-6xl">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-8">
            <div className="flex items-center gap-3 text-slate-300">
              <RefreshCw className="h-5 w-5 animate-spin" />
              Loading dashboard...
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen bg-slate-950 px-6 py-10 text-white">
        <div className="mx-auto max-w-4xl">
          <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-8">
            <div className="flex items-start gap-3">
              <AlertCircle className="mt-1 h-6 w-6 shrink-0 text-red-300" />

              <div>
                <h1 className="text-2xl font-bold text-red-100">
                  Could not load dashboard
                </h1>

                <p className="mt-3 text-red-100">{error}</p>

                <div className="mt-6 flex flex-wrap gap-3">
                  <button
                    onClick={() => loadDashboard(true)}
                    className="rounded-xl bg-white px-5 py-3 text-sm font-bold text-slate-950 hover:bg-slate-200"
                  >
                    Try Again
                  </button>

                  <Link
                    href="/login"
                    className="inline-flex items-center gap-2 rounded-xl border border-red-300/40 px-5 py-3 text-sm font-bold text-red-50 hover:bg-red-500/10"
                  >
                    <LogIn className="h-4 w-4" />
                    Login
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-10 text-white">
      <div className="mx-auto max-w-6xl">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-300">
              <ShieldCheck className="h-4 w-4" />
              Logged In
            </div>

            <h1 className="mt-5 text-3xl font-bold tracking-tight md:text-4xl">
              Dashboard
            </h1>

            <p className="mt-2 text-slate-400">
              Welcome,{" "}
              <span className="font-semibold text-slate-200">
                {user?.email || "User"}
              </span>
            </p>

            <p className="mt-1 text-sm text-slate-500">
              Role: {user?.role || "user"}
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            {user?.role === "admin" && (
              <Link
                href="/admin"
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-5 py-3 text-sm font-bold text-white hover:bg-slate-800"
              >
                <BarChart3 className="h-4 w-4" />
                Admin Panel
              </Link>
            )}

            <button
              onClick={() => loadDashboard(true)}
              disabled={refreshing}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-5 py-3 text-sm font-bold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <RefreshCw
                className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
              />
              Refresh
            </button>

            <Link
              href="/upload"
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-bold text-slate-950 hover:bg-slate-200"
            >
              <Upload className="h-4 w-4" />
              Upload New
            </Link>
          </div>
        </div>

        <section className="mb-6 grid gap-6 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
            <p className="text-sm text-slate-400">Total Uploads</p>
            <p className="mt-3 text-4xl font-extrabold">{uploads.length}</p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
            <p className="text-sm text-slate-400">Completed</p>
            <p className="mt-3 text-4xl font-extrabold">
              {
                uploads.filter(
                  (upload) => upload.analysis_status === "completed"
                ).length
              }
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
            <p className="text-sm text-slate-400">Pending / Queued</p>
            <p className="mt-3 text-4xl font-extrabold">
              {
                uploads.filter(
                  (upload) =>
                    upload.analysis_status === "queued" ||
                    upload.analysis_status === "processing" ||
                    !upload.analysis_status
                ).length
              }
            </p>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
          <div className="flex items-center gap-3">
            <FileImage className="h-6 w-6 text-slate-300" />
            <h2 className="text-xl font-bold">Upload History</h2>
          </div>

          {uploads.length === 0 ? (
            <div className="mt-6 rounded-2xl border border-dashed border-slate-700 bg-slate-950/60 p-10 text-center">
              <Clock3 className="mx-auto h-12 w-12 text-slate-600" />

              <h3 className="mt-4 text-lg font-bold text-slate-200">
                No uploads yet
              </h3>

              <p className="mt-2 text-sm text-slate-500">
                Upload your first image or video to start analysis.
              </p>

              <Link
                href="/upload"
                className="mt-6 inline-flex items-center justify-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-bold text-slate-950 hover:bg-slate-200"
              >
                <Upload className="h-4 w-4" />
                Upload Media
              </Link>
            </div>
          ) : (
            <div className="mt-6 overflow-x-auto">
              <table className="w-full min-w-[940px] border-separate border-spacing-y-2 text-left text-sm">
                <thead className="text-slate-400">
                  <tr>
                    <th className="px-4 py-2">File</th>
                    <th className="px-4 py-2">Type</th>
                    <th className="px-4 py-2">Size</th>
                    <th className="px-4 py-2">Upload Status</th>
                    <th className="px-4 py-2">Analysis Status</th>
                    <th className="px-4 py-2">Uploaded At</th>
                    <th className="px-4 py-2 text-right">Action</th>
                  </tr>
                </thead>

                <tbody>
                  {uploads.map((upload) => {
                    const uploadId = getUploadId(upload);
                    const resultHref = upload.job_id
                      ? `/result?job_id=${upload.job_id}`
                      : `/result?upload_id=${uploadId}`;

                    return (
                      <tr key={uploadId} className="bg-slate-950/70">
                        <td className="rounded-l-xl px-4 py-4">
                          <p className="max-w-[260px] truncate font-semibold text-slate-200">
                            {upload.original_filename}
                          </p>
                          <p className="mt-1 text-xs text-slate-500">
                            {upload.mime_type}
                          </p>
                        </td>

                        <td className="px-4 py-4 text-slate-300">
                          {upload.file_type}
                        </td>

                        <td className="px-4 py-4 text-slate-300">
                          {formatFileSize(upload.file_size_bytes)}
                        </td>

                        <td className="px-4 py-4">
                          <span
                            className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${getStatusStyle(
                              upload.upload_status
                            )}`}
                          >
                            {upload.upload_status}
                          </span>
                        </td>

                        <td className="px-4 py-4">
                          <span
                            className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${getStatusStyle(
                              upload.analysis_status || "queued"
                            )}`}
                          >
                            {upload.analysis_status || "queued"}
                          </span>
                        </td>

                        <td className="px-4 py-4 text-slate-300">
                          {formatDate(upload.created_at)}
                        </td>

                        <td className="rounded-r-xl px-4 py-4 text-right">
                          <Link
                            href={resultHref}
                            className="inline-flex items-center justify-center rounded-xl border border-slate-700 px-4 py-2 text-xs font-bold text-slate-100 hover:bg-slate-900"
                          >
                            View Result
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}