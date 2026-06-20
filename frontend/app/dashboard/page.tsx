"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  BarChart3,
  Brain,
  Clock3,
  FileImage,
  FileVideo,
  Filter,
  LogOut,
  RefreshCw,
  Search,
  ShieldAlert,
  Upload,
} from "lucide-react";

import { getDashboardJobs } from "@/lib/dashboard";
import type { DashboardJobItem } from "@/types/dashboard";

const TOKEN_KEY = "deepfake_access_token";
const USER_KEY = "deepfake_user";

type StoredUser = {
  id?: string;
  email?: string;
  role?: string;
  full_name?: string;
};

function formatDate(value: string | null | undefined) {
  if (!value) {
    return "N/A";
  }

  return new Date(value).toLocaleString();
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "N/A";
  }

  return `${Math.round(value * 100)}%`;
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

function getRiskLabel(riskLevel?: string | null) {
  switch (riskLevel) {
    case "likely_authentic":
      return "Likely Authentic";

    case "uncertain":
      return "Uncertain";

    case "suspicious":
      return "Suspicious";

    case "high_risk":
      return "High Risk";

    default:
      return "N/A";
  }
}

function getBadgeStyle(value?: string | null) {
  switch (value) {
    case "completed":
    case "likely_authentic":
      return "border-emerald-500/40 bg-emerald-500/10 text-emerald-300";

    case "processing":
      return "border-blue-500/40 bg-blue-500/10 text-blue-300";

    case "queued":
    case "uncertain":
      return "border-yellow-500/40 bg-yellow-500/10 text-yellow-300";

    case "suspicious":
      return "border-orange-500/40 bg-orange-500/10 text-orange-300";

    case "failed":
    case "high_risk":
      return "border-red-500/40 bg-red-500/10 text-red-300";

    default:
      return "border-slate-500/40 bg-slate-500/10 text-slate-300";
  }
}

function MediaIcon({
  fileType,
  className,
}: {
  fileType?: string;
  className: string;
}) {
  if (fileType === "video") {
    return <FileVideo className={className} />;
  }

  return <FileImage className={className} />;
}

export default function DashboardPage() {
  const [jobs, setJobs] = useState<DashboardJobItem[]>([]);
  const [user, setUser] = useState<StoredUser | null>(null);

  const [searchText, setSearchText] = useState("");
  const [jobStatus, setJobStatus] = useState("all");
  const [riskLevel, setRiskLevel] = useState("all");
  const [mediaType, setMediaType] = useState("all");
  const [limit, setLimit] = useState(100);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const summary = useMemo(() => {
    return {
      total: jobs.length,
      completed: jobs.filter((job) => job.job_status === "completed").length,
      queued: jobs.filter((job) => job.job_status === "queued").length,
      highRisk: jobs.filter((job) => job.risk_level === "high_risk").length,
    };
  }, [jobs]);

  async function loadDashboard(isRefresh = false) {
    try {
      setError("");

      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      const token = localStorage.getItem(TOKEN_KEY);

      if (!token) {
        throw new Error("You are not logged in. Please login first.");
      }

      const storedUser = localStorage.getItem(USER_KEY);

      if (storedUser) {
        setUser(JSON.parse(storedUser) as StoredUser);
      }

      const jobItems = await getDashboardJobs(token, {
        search: searchText,
        jobStatus,
        riskLevel,
        mediaType,
        limit,
      });

      setJobs(Array.isArray(jobItems) ? jobItems : []);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load dashboard."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  function resetFilters() {
    setSearchText("");
    setJobStatus("all");
    setRiskLevel("all");
    setMediaType("all");
    setLimit(100);
  }

  function handleLogout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    window.location.href = "/login";
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadDashboard(false);
    }, 0);

    return () => {
      window.clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-950 px-6 py-10 text-white">
        <div className="mx-auto max-w-7xl rounded-2xl border border-slate-800 bg-slate-900/70 p-8">
          <div className="flex items-center gap-3 text-slate-300">
            <RefreshCw className="h-5 w-5 animate-spin" />
            Loading dashboard...
          </div>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen bg-slate-950 px-6 py-10 text-white">
        <div className="mx-auto max-w-4xl rounded-2xl border border-red-500/30 bg-red-500/10 p-8">
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-1 h-6 w-6 text-red-300" />

            <div>
              <h1 className="text-2xl font-bold text-red-100">
                Dashboard Error
              </h1>

              <p className="mt-3 text-red-100">{error}</p>

              <div className="mt-6 flex flex-wrap gap-3">
                <button
                  onClick={() => void loadDashboard(true)}
                  className="rounded-xl bg-white px-5 py-3 text-sm font-bold text-slate-950 hover:bg-slate-200"
                >
                  Try Again
                </button>

                <Link
                  href="/login"
                  className="rounded-xl border border-red-300/40 px-5 py-3 text-sm font-bold text-red-50 hover:bg-red-500/10"
                >
                  Login
                </Link>
              </div>
            </div>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-10 text-white">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-blue-500/30 bg-blue-500/10 px-4 py-2 text-sm font-semibold text-blue-300">
              <Brain className="h-4 w-4" />
              Deepfake Detection Dashboard
            </div>

            <h1 className="mt-5 text-3xl font-bold tracking-tight md:text-4xl">
              My Analysis History
            </h1>

            <p className="mt-2 text-slate-400">
              {user?.email
                ? `Logged in as ${user.email}`
                : "View and filter your uploaded media analysis results."}
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <Link
              href="/upload"
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-bold text-slate-950 hover:bg-slate-200"
            >
              <Upload className="h-4 w-4" />
              New Upload
            </Link>

            {user?.role === "admin" && (
              <Link
                href="/admin"
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-5 py-3 text-sm font-bold text-white hover:bg-slate-800"
              >
                Admin Panel
              </Link>
            )}

            <Link
              href="/system"
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-5 py-3 text-sm font-bold text-white hover:bg-slate-800"
            >
              System Health
            </Link>

            <button
              onClick={handleLogout}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-red-500/40 px-5 py-3 text-sm font-bold text-red-200 hover:bg-red-500/10"
            >
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </div>
        </div>

        <section className="mb-6 grid gap-6 md:grid-cols-4">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
            <p className="text-sm text-slate-400">Total Results</p>
            <p className="mt-3 text-4xl font-extrabold">{summary.total}</p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
            <p className="text-sm text-slate-400">Completed</p>
            <p className="mt-3 text-4xl font-extrabold">
              {summary.completed}
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
            <p className="text-sm text-slate-400">Queued</p>
            <p className="mt-3 text-4xl font-extrabold">{summary.queued}</p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
            <p className="text-sm text-slate-400">High Risk</p>
            <p className="mt-3 text-4xl font-extrabold">{summary.highRisk}</p>
          </div>
        </section>

        <section className="mb-6 rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
          <div className="flex items-center gap-3">
            <Filter className="h-6 w-6 text-slate-300" />
            <h2 className="text-xl font-bold">Search and Filters</h2>
          </div>

          <div className="mt-5 grid gap-4 md:grid-cols-5">
            <div className="md:col-span-2">
              <label className="text-sm text-slate-400">Search</label>
              <div className="mt-2 flex items-center rounded-xl border border-slate-700 bg-slate-950 px-4">
                <Search className="h-4 w-4 text-slate-500" />
                <input
                  value={searchText}
                  onChange={(event) => setSearchText(event.target.value)}
                  placeholder="filename, job id, upload id"
                  className="w-full bg-transparent px-3 py-3 text-sm text-white outline-none placeholder:text-slate-600"
                />
              </div>
            </div>

            <div>
              <label className="text-sm text-slate-400">Job Status</label>
              <select
                value={jobStatus}
                onChange={(event) => setJobStatus(event.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-white outline-none focus:border-slate-500"
              >
                <option value="all">All</option>
                <option value="queued">Queued</option>
                <option value="processing">Processing</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
              </select>
            </div>

            <div>
              <label className="text-sm text-slate-400">Risk Level</label>
              <select
                value={riskLevel}
                onChange={(event) => setRiskLevel(event.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-white outline-none focus:border-slate-500"
              >
                <option value="all">All</option>
                <option value="likely_authentic">Likely Authentic</option>
                <option value="uncertain">Uncertain</option>
                <option value="suspicious">Suspicious</option>
                <option value="high_risk">High Risk</option>
                <option value="not_available">Not Available</option>
              </select>
            </div>

            <div>
              <label className="text-sm text-slate-400">Media Type</label>
              <select
                value={mediaType}
                onChange={(event) => setMediaType(event.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-white outline-none focus:border-slate-500"
              >
                <option value="all">All</option>
                <option value="image">Image</option>
                <option value="video">Video</option>
              </select>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <div>
              <label className="text-sm text-slate-400">Limit</label>
              <select
                value={limit}
                onChange={(event) => setLimit(Number(event.target.value))}
                className="ml-3 rounded-xl border border-slate-700 bg-slate-950 px-4 py-2.5 text-sm text-white outline-none focus:border-slate-500"
              >
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={200}>200</option>
                <option value={300}>300</option>
              </select>
            </div>

            <button
              onClick={() => void loadDashboard(true)}
              disabled={refreshing}
              className="rounded-xl bg-white px-5 py-2.5 text-sm font-bold text-slate-950 hover:bg-slate-200 disabled:opacity-60"
            >
              {refreshing ? "Applying..." : "Apply Filters"}
            </button>

            <button
              onClick={resetFilters}
              className="rounded-xl border border-slate-700 px-5 py-2.5 text-sm font-bold text-slate-200 hover:bg-slate-800"
            >
              Reset
            </button>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
          <div className="flex items-center gap-3">
            <BarChart3 className="h-6 w-6 text-slate-300" />
            <h2 className="text-xl font-bold">My Jobs</h2>
          </div>

          <div className="mt-6 overflow-x-auto">
            <table className="w-full min-w-[1050px] border-separate border-spacing-y-2 text-left text-sm">
              <thead className="text-slate-400">
                <tr>
                  <th className="px-4 py-2">File</th>
                  <th className="px-4 py-2">Job Status</th>
                  <th className="px-4 py-2">Risk</th>
                  <th className="px-4 py-2">Score</th>
                  <th className="px-4 py-2">Uploaded</th>
                  <th className="px-4 py-2">Size</th>
                  <th className="px-4 py-2 text-right">Action</th>
                </tr>
              </thead>

              <tbody>
                {jobs.length === 0 ? (
                  <tr>
                    <td
                      colSpan={7}
                      className="rounded-xl bg-slate-950 px-4 py-8 text-center text-slate-400"
                    >
                      <ShieldAlert className="mx-auto mb-3 h-8 w-8 text-slate-600" />
                      No jobs found for the selected filters.
                    </td>
                  </tr>
                ) : (
                  jobs.map((job) => (
                    <tr key={job.job_id} className="bg-slate-950/70">
                      <td className="rounded-l-xl px-4 py-4">
                        <div className="flex items-center gap-3">
                          <MediaIcon
                            fileType={job.file_type}
                            className="h-5 w-5 text-slate-500"
                          />

                          <div>
                            <p className="max-w-[300px] truncate font-semibold text-slate-200">
                              {job.original_filename}
                            </p>
                            <p className="mt-1 text-xs text-slate-500">
                              {job.file_type} · {job.mime_type}
                            </p>
                          </div>
                        </div>
                      </td>

                      <td className="px-4 py-4">
                        <span
                          className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${getBadgeStyle(
                            job.job_status
                          )}`}
                        >
                          {job.job_status}
                        </span>
                      </td>

                      <td className="px-4 py-4">
                        <span
                          className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${getBadgeStyle(
                            job.risk_level
                          )}`}
                        >
                          {getRiskLabel(job.risk_level)}
                        </span>
                      </td>

                      <td className="px-4 py-4 text-slate-300">
                        {formatPercent(job.final_score)}
                      </td>

                      <td className="px-4 py-4 text-slate-300">
                        {formatDate(job.uploaded_at)}
                      </td>

                      <td className="px-4 py-4 text-slate-300">
                        {formatFileSize(job.file_size_bytes)}
                      </td>

                      <td className="rounded-r-xl px-4 py-4 text-right">
                        <Link
                          href={`/result?job_id=${job.job_id}`}
                          className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-2 text-xs font-bold text-slate-100 hover:bg-slate-900"
                        >
                          View Result
                          <ArrowRight className="h-3 w-3" />
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}