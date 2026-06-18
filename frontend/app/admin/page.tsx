"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  AlertCircle,
  ArrowLeft,
  BarChart3,
  Clock3,
  FileImage,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";

import { getAdminJobs, getAdminOverview } from "@/lib/admin";
import type { AdminJobItem, AdminOverview } from "@/types/admin";

const TOKEN_KEY = "deepfake_access_token";

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

    case "high_risk":
      return "border-red-500/40 bg-red-500/10 text-red-300";

    case "suspicious":
      return "border-orange-500/40 bg-orange-500/10 text-orange-300";

    case "uncertain":
      return "border-yellow-500/40 bg-yellow-500/10 text-yellow-300";

    case "likely_authentic":
      return "border-emerald-500/40 bg-emerald-500/10 text-emerald-300";

    default:
      return "border-slate-500/40 bg-slate-500/10 text-slate-300";
  }
}

export default function AdminPage() {
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [jobs, setJobs] = useState<AdminJobItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  async function loadAdmin(isRefresh = false) {
    try {
      setError("");

      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      const token = localStorage.getItem(TOKEN_KEY);

      if (!token) {
        throw new Error("You are not logged in.");
      }

      const [overviewData, jobItems] = await Promise.all([
        getAdminOverview(token),
        getAdminJobs(token),
      ]);

      setOverview(overviewData);
      setJobs(jobItems);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load admin.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      loadAdmin();
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
            Loading admin panel...
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
                Admin Panel Error
              </h1>
              <p className="mt-3 text-red-100">{error}</p>
              <div className="mt-6 flex gap-3">
                <button
                  onClick={() => loadAdmin(true)}
                  className="rounded-xl bg-white px-5 py-3 text-sm font-bold text-slate-950 hover:bg-slate-200"
                >
                  Try Again
                </button>
                <Link
                  href="/dashboard"
                  className="rounded-xl border border-red-300/40 px-5 py-3 text-sm font-bold text-red-50 hover:bg-red-500/10"
                >
                  Dashboard
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
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <Link
              href="/dashboard"
              className="mb-4 inline-flex items-center gap-2 text-sm text-slate-300 hover:text-white"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Dashboard
            </Link>

            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-300">
              <ShieldCheck className="h-4 w-4" />
              Admin Access
            </div>

            <h1 className="mt-5 text-3xl font-bold tracking-tight md:text-4xl">
              Admin Monitoring Panel
            </h1>

            <p className="mt-2 text-slate-400">
              Monitor uploads, jobs, and analysis results.
            </p>
          </div>

          <button
            onClick={() => loadAdmin(true)}
            disabled={refreshing}
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-5 py-3 text-sm font-bold text-white hover:bg-slate-800 disabled:opacity-60"
          >
            <RefreshCw
              className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
            />
            Refresh
          </button>
        </div>

        <section className="mb-6 grid gap-6 md:grid-cols-4">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
            <p className="text-sm text-slate-400">Total Uploads</p>
            <p className="mt-3 text-4xl font-extrabold">
              {overview?.uploads.total_uploads || 0}
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
            <p className="text-sm text-slate-400">Total Jobs</p>
            <p className="mt-3 text-4xl font-extrabold">
              {overview?.jobs.total_jobs || 0}
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
            <p className="text-sm text-slate-400">Completed Jobs</p>
            <p className="mt-3 text-4xl font-extrabold">
              {overview?.jobs.completed_jobs || 0}
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
            <p className="text-sm text-slate-400">High Risk</p>
            <p className="mt-3 text-4xl font-extrabold">
              {overview?.results.high_risk_count || 0}
            </p>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
          <div className="flex items-center gap-3">
            <BarChart3 className="h-6 w-6 text-slate-300" />
            <h2 className="text-xl font-bold">Latest Analysis Jobs</h2>
          </div>

          <div className="mt-6 overflow-x-auto">
            <table className="w-full min-w-[1100px] border-separate border-spacing-y-2 text-left text-sm">
              <thead className="text-slate-400">
                <tr>
                  <th className="px-4 py-2">File</th>
                  <th className="px-4 py-2">User</th>
                  <th className="px-4 py-2">Job</th>
                  <th className="px-4 py-2">Risk</th>
                  <th className="px-4 py-2">Score</th>
                  <th className="px-4 py-2">Queued</th>
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
                      <Clock3 className="mx-auto mb-3 h-8 w-8 text-slate-600" />
                      No jobs found.
                    </td>
                  </tr>
                ) : (
                  jobs.map((job) => (
                    <tr key={job.job_id} className="bg-slate-950/70">
                      <td className="rounded-l-xl px-4 py-4">
                        <div className="flex items-center gap-3">
                          <FileImage className="h-5 w-5 text-slate-500" />
                          <div>
                            <p className="max-w-[260px] truncate font-semibold text-slate-200">
                              {job.original_filename}
                            </p>
                            <p className="mt-1 text-xs text-slate-500">
                              {job.file_type} · {job.mime_type}
                            </p>
                          </div>
                        </div>
                      </td>

                      <td className="px-4 py-4 text-slate-300">
                        {job.user_email}
                      </td>

                      <td className="px-4 py-4">
                        <span
                          className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${getStatusStyle(
                            job.job_status
                          )}`}
                        >
                          {job.job_status}
                        </span>
                      </td>

                      <td className="px-4 py-4">
                        <span
                          className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${getStatusStyle(
                            job.risk_level
                          )}`}
                        >
                          {job.risk_level || "N/A"}
                        </span>
                      </td>

                      <td className="px-4 py-4 text-slate-300">
                        {formatPercent(job.final_score)}
                      </td>

                      <td className="px-4 py-4 text-slate-300">
                        {formatDate(job.queued_at)}
                      </td>

                      <td className="rounded-r-xl px-4 py-4 text-right">
                        <Link
                          href={`/result?job_id=${job.job_id}`}
                          className="inline-flex rounded-xl border border-slate-700 px-4 py-2 text-xs font-bold text-slate-100 hover:bg-slate-900"
                        >
                          View Result
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