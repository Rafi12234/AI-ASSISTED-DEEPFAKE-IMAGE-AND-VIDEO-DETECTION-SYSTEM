"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  Brain,
  CheckCircle2,
  Clock3,
  Download,
  FileImage,
  FileVideo,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";

import { getResultByJobId, getResultByUploadId } from "@/lib/results";
import { downloadResultReportPdf } from "@/lib/reports";
import type { AnalysisResultResponse, SampledFrameResult } from "@/types/result";

const TOKEN_KEY = "deepfake_access_token";

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "N/A";
  }

  return `${Math.round(value * 100)}%`;
}

function formatDecimal(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "N/A";
  }

  return value.toFixed(4);
}

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

function getRiskLabel(riskLevel?: string) {
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
      return riskLevel || "Pending";
  }
}

function getRiskClassName(riskLevel?: string) {
  switch (riskLevel) {
    case "likely_authentic":
      return "border-emerald-500/40 bg-emerald-500/10 text-emerald-300";

    case "uncertain":
      return "border-yellow-500/40 bg-yellow-500/10 text-yellow-300";

    case "suspicious":
      return "border-orange-500/40 bg-orange-500/10 text-orange-300";

    case "high_risk":
      return "border-red-500/40 bg-red-500/10 text-red-300";

    default:
      return "border-slate-500/40 bg-slate-500/10 text-slate-300";
  }
}

function getStatusStyle(status?: string) {
  switch (status) {
    case "completed":
      return "border-emerald-500/40 bg-emerald-500/10 text-emerald-300";

    case "processing":
      return "border-blue-500/40 bg-blue-500/10 text-blue-300";

    case "queued":
      return "border-yellow-500/40 bg-yellow-500/10 text-yellow-300";

    case "failed":
      return "border-red-500/40 bg-red-500/10 text-red-300";

    default:
      return "border-slate-500/40 bg-slate-500/10 text-slate-300";
  }
}

function RiskIcon({ riskLevel, className }: { riskLevel?: string; className: string }) {
  if (riskLevel === "likely_authentic") {
    return <ShieldCheck className={className} />;
  }

  if (riskLevel === "uncertain") {
    return <AlertTriangle className={className} />;
  }

  if (riskLevel === "suspicious" || riskLevel === "high_risk") {
    return <ShieldAlert className={className} />;
  }

  return <Clock3 className={className} />;
}

function MediaIcon({ fileType, className }: { fileType?: string; className: string }) {
  if (fileType === "video") {
    return <FileVideo className={className} />;
  }

  return <FileImage className={className} />;
}

function getAverageFrameScore(frames: SampledFrameResult[]) {
  if (frames.length === 0) {
    return null;
  }

  const total = frames.reduce((sum, frame) => sum + frame.final_score, 0);
  return total / frames.length;
}

function getMaxFrameScore(frames: SampledFrameResult[]) {
  if (frames.length === 0) {
    return null;
  }

  return Math.max(...frames.map((frame) => frame.final_score));
}

export default function ResultClient() {
  const searchParams = useSearchParams();

  const jobId = searchParams.get("job_id");
  const uploadId = searchParams.get("upload_id");

  const [data, setData] = useState<AnalysisResultResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [pageError, setPageError] = useState("");
  const [actionError, setActionError] = useState("");

  const sampledFrames = useMemo(() => {
    return data?.result?.signals_summary?.sampled_frames || [];
  }, [data?.result?.signals_summary?.sampled_frames]);

  const averageFrameScore = useMemo(() => {
    return getAverageFrameScore(sampledFrames);
  }, [sampledFrames]);

  const maxFrameScore = useMemo(() => {
    return getMaxFrameScore(sampledFrames);
  }, [sampledFrames]);

  const isVideoResult = data?.job.file_type === "video" || sampledFrames.length > 0;

  const loadResult = useCallback(
    async (isRefresh = false) => {
      try {
        setPageError("");
        setActionError("");

        if (isRefresh) {
          setRefreshing(true);
        } else {
          setLoading(true);
        }

        const token = localStorage.getItem(TOKEN_KEY);

        if (!token) {
          throw new Error("You are not logged in. Please login first.");
        }

        if (!jobId && !uploadId) {
          throw new Error("No job_id or upload_id found in the URL.");
        }

        const result = jobId
          ? await getResultByJobId(jobId, token)
          : await getResultByUploadId(uploadId as string, token);

        setData(result);
      } catch (err) {
        setPageError(
          err instanceof Error ? err.message : "Something went wrong."
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [jobId, uploadId]
  );

  async function handleDownloadPdf() {
    try {
      setActionError("");

      if (!data?.job?.job_id) {
        throw new Error("Job ID is missing.");
      }

      if (!data.result) {
        throw new Error(
          "PDF report is available only after analysis is completed."
        );
      }

      const token = localStorage.getItem(TOKEN_KEY);

      if (!token) {
        throw new Error("You are not logged in. Please login first.");
      }

      setDownloadingPdf(true);

      await downloadResultReportPdf(data.job.job_id, token);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "PDF download failed.");
    } finally {
      setDownloadingPdf(false);
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadResult(false);
    }, 0);

    return () => {
      window.clearTimeout(timer);
    };
  }, [loadResult]);

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-950 px-6 py-10 text-white">
        <div className="mx-auto max-w-6xl">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-8">
            <div className="flex items-center gap-3 text-slate-300">
              <RefreshCw className="h-5 w-5 animate-spin" />
              Loading analysis result...
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (pageError) {
    return (
      <main className="min-h-screen bg-slate-950 px-6 py-10 text-white">
        <div className="mx-auto max-w-4xl">
          <Link
            href="/dashboard"
            className="mb-6 inline-flex items-center gap-2 text-sm text-slate-300 hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </Link>

          <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-8">
            <h1 className="text-2xl font-bold text-red-200">
              Could not load result
            </h1>
            <p className="mt-3 text-red-100">{pageError}</p>

            <div className="mt-6 flex flex-wrap gap-3">
              <button
                onClick={() => void loadResult(true)}
                className="rounded-xl bg-white px-5 py-2.5 text-sm font-semibold text-slate-950 hover:bg-slate-200"
              >
                Try Again
              </button>

              <Link
                href="/login"
                className="rounded-xl border border-slate-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-slate-900"
              >
                Login
              </Link>
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-10 text-white">
      <div className="mx-auto max-w-6xl">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <Link
              href="/dashboard"
              className="mb-4 inline-flex items-center gap-2 text-sm text-slate-300 hover:text-white"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Dashboard
            </Link>

            <h1 className="text-3xl font-bold tracking-tight md:text-4xl">
              Analysis Result
            </h1>

            <p className="mt-2 text-slate-400">
              {isVideoResult
                ? "Video frame analysis result for your uploaded media."
                : "Image analysis result for your uploaded media."}
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => void handleDownloadPdf()}
              disabled={downloadingPdf || !data.result}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-white px-5 py-2.5 text-sm font-semibold text-slate-950 hover:bg-slate-200 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Download className="h-4 w-4" />
              {downloadingPdf ? "Downloading..." : "Download PDF"}
            </button>

            <button
              onClick={() => void loadResult(true)}
              disabled={refreshing}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <RefreshCw
                className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
              />
              Refresh
            </button>
          </div>
        </div>

        {actionError && (
          <div className="mb-6 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-100">
            {actionError}
          </div>
        )}

        <section className="grid gap-6 lg:grid-cols-3">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 lg:col-span-2">
            <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-sm font-medium text-slate-400">
                  Overall Risk Level
                </p>

                <div
                  className={`mt-3 inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-bold ${getRiskClassName(
                    data.result?.risk_level
                  )}`}
                >
                  <RiskIcon
                    riskLevel={data.result?.risk_level}
                    className="h-4 w-4"
                  />
                  {getRiskLabel(data.result?.risk_level)}
                </div>
              </div>

              <div className="text-left md:text-right">
                <p className="text-sm font-medium text-slate-400">
                  Final Score
                </p>
                <p className="mt-2 text-5xl font-extrabold">
                  {formatPercent(data.result?.final_score)}
                </p>
              </div>
            </div>

            <div className="mt-8 h-4 overflow-hidden rounded-full bg-slate-800">
              <div
                className="h-full rounded-full bg-white"
                style={{
                  width: `${Math.min(
                    Math.max((data.result?.final_score || 0) * 100, 0),
                    100
                  )}%`,
                }}
              />
            </div>

            <div className="mt-8 rounded-xl border border-slate-800 bg-slate-950/60 p-5">
              <p className="text-sm font-semibold text-slate-300">
                Explanation
              </p>
              <p className="mt-2 leading-7 text-slate-300">
                {data.result?.explanation ||
                  data.message ||
                  "Analysis result is not available yet."}
              </p>
            </div>
            {data.result?.signals_summary?.interpretation && (
  <div className="mt-6 rounded-xl border border-slate-800 bg-slate-950/60 p-5">
    <p className="text-sm font-semibold text-slate-300">
      Interpretation
    </p>

    <div className="mt-4 grid gap-4 md:grid-cols-2">
      <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-4">
        <p className="text-xs uppercase tracking-wide text-slate-500">
          Score Meaning
        </p>
        <p className="mt-2 text-sm leading-6 text-slate-300">
          {
            data.result.signals_summary.interpretation
              .score_interpretation
          }
        </p>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-4">
        <p className="text-xs uppercase tracking-wide text-slate-500">
          Recommended Action
        </p>
        <p className="mt-2 text-sm leading-6 text-slate-300">
          {
            data.result.signals_summary.interpretation
              .recommended_action
          }
        </p>
      </div>
    </div>

    {data.result.signals_summary.interpretation.top_signals &&
      data.result.signals_summary.interpretation.top_signals.length >
        0 && (
        <div className="mt-5">
          <p className="text-xs uppercase tracking-wide text-slate-500">
            Top Contributing Signals
          </p>

          <div className="mt-3 grid gap-3 md:grid-cols-3">
            {data.result.signals_summary.interpretation.top_signals.map(
              (signal) => (
                <div
                  key={`${signal.signal_type}-${signal.signal_name}`}
                  className="rounded-xl border border-slate-800 bg-slate-900/80 p-4"
                >
                  <p className="font-semibold text-slate-200">
                    {signal.signal_name || signal.signal_type}
                  </p>

                  <p className="mt-2 text-2xl font-extrabold">
                    {formatPercent(signal.score)}
                  </p>

                  <p className="mt-2 text-xs text-slate-500">
                    Severity: {signal.severity || "N/A"}
                  </p>
                </div>
              )
            )}
          </div>
        </div>
      )}

    {data.result.signals_summary.interpretation.limitations &&
      data.result.signals_summary.interpretation.limitations.length >
        0 && (
        <div className="mt-5 rounded-xl border border-yellow-500/30 bg-yellow-500/10 p-4">
          <p className="text-sm font-semibold text-yellow-100">
            Limitations
          </p>

          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-yellow-100/90">
            {data.result.signals_summary.interpretation.limitations.map(
              (item) => (
                <li key={item}>{item}</li>
              )
            )}
          </ul>
        </div>
      )}
  </div>
)}

            {!data.result && (
              <div className="mt-6 rounded-xl border border-yellow-500/30 bg-yellow-500/10 p-5 text-yellow-100">
                This job is not completed yet. Wait for the worker and refresh
                this page.
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
            <div className="flex items-center gap-3">
              <MediaIcon fileType={data.job.file_type} className="h-5 w-5 text-slate-300" />
              <h2 className="text-lg font-bold">Media Information</h2>
            </div>

            <div className="mt-5 space-y-4 text-sm">
              <div>
                <p className="text-slate-500">Filename</p>
                <p className="mt-1 break-words text-slate-200">
                  {data.job.original_filename}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-slate-500">Type</p>
                  <p className="mt-1 text-slate-200">{data.job.file_type}</p>
                </div>

                <div>
                  <p className="text-slate-500">Size</p>
                  <p className="mt-1 text-slate-200">
                    {formatFileSize(data.job.file_size_bytes)}
                  </p>
                </div>
              </div>

              <div>
                <p className="text-slate-500">MIME Type</p>
                <p className="mt-1 text-slate-200">{data.job.mime_type}</p>
              </div>

              <div>
                <p className="text-slate-500">Upload Status</p>
                <p className="mt-1 text-slate-200">{data.job.upload_status}</p>
              </div>
            </div>
          </div>
        </section>

        <section className="mt-6 grid gap-6 lg:grid-cols-4">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
            <div className="flex items-center gap-3">
              <Activity className="h-5 w-5 text-slate-300" />
              <h2 className="text-lg font-bold">Job Status</h2>
            </div>

            <div className="mt-5">
              <span
                className={`inline-flex rounded-full border px-3 py-1 text-sm font-semibold ${getStatusStyle(
                  data.job.job_status
                )}`}
              >
                {data.job.job_status}
              </span>
            </div>

            <p className="mt-4 text-xs text-slate-500">
              Completed: {formatDate(data.job.completed_at)}
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-5 w-5 text-slate-300" />
              <h2 className="text-lg font-bold">Confidence</h2>
            </div>

            <p className="mt-5 text-4xl font-extrabold">
              {formatPercent(data.result?.confidence)}
            </p>

            <p className="mt-3 text-sm text-slate-400">
              {data.result?.processing_time_ms
                ? `${data.result.processing_time_ms} ms`
                : "N/A"}
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
            <div className="flex items-center gap-3">
              <Brain className="h-5 w-5 text-slate-300" />
              <h2 className="text-lg font-bold">Engine</h2>
            </div>

            <p className="mt-5 break-words text-lg font-semibold text-slate-200">
              {data.result?.model_versions?.engine || "N/A"}
            </p>

            <p className="mt-3 text-sm text-slate-400">
              Foundation analysis service.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
            <div className="flex items-center gap-3">
              <BarChart3 className="h-5 w-5 text-slate-300" />
              <h2 className="text-lg font-bold">Frame Stats</h2>
            </div>

            <p className="mt-5 text-4xl font-extrabold">
              {sampledFrames.length}
            </p>

            <p className="mt-3 text-sm text-slate-400">
              sampled frames
            </p>
          </div>
        </section>

        {isVideoResult && (
          <section className="mt-6 rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
            <h2 className="text-xl font-bold">Video Frame Analysis</h2>

            <div className="mt-5 grid gap-4 md:grid-cols-3">
              <div className="rounded-xl border border-slate-800 bg-slate-950 p-5">
                <p className="text-sm text-slate-500">Sampled Frames</p>
                <p className="mt-2 text-3xl font-extrabold">
                  {sampledFrames.length}
                </p>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-950 p-5">
                <p className="text-sm text-slate-500">Average Frame Score</p>
                <p className="mt-2 text-3xl font-extrabold">
                  {formatPercent(averageFrameScore)}
                </p>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-950 p-5">
                <p className="text-sm text-slate-500">Max Frame Score</p>
                <p className="mt-2 text-3xl font-extrabold">
                  {formatPercent(maxFrameScore)}
                </p>
              </div>
            </div>

            <div className="mt-6 overflow-x-auto">
              <table className="w-full min-w-[760px] border-separate border-spacing-y-2 text-left text-sm">
                <thead className="text-slate-400">
                  <tr>
                    <th className="px-4 py-2">Frame</th>
                    <th className="px-4 py-2">Timestamp</th>
                    <th className="px-4 py-2">Score</th>
                    <th className="px-4 py-2">Raw Score</th>
                    <th className="px-4 py-2">Risk Level</th>
                    <th className="px-4 py-2">Confidence</th>
                  </tr>
                </thead>

                <tbody>
                  {sampledFrames.length === 0 ? (
                    <tr>
                      <td
                        colSpan={6}
                        className="rounded-xl bg-slate-950 px-4 py-4 text-slate-400"
                      >
                        No sampled frame data available.
                      </td>
                    </tr>
                  ) : (
                    sampledFrames.map((frame) => (
                      <tr key={`${frame.frame_number}-${frame.timestamp_seconds}`} className="bg-slate-950/70">
                        <td className="rounded-l-xl px-4 py-4 font-semibold text-slate-200">
                          #{frame.frame_number}
                        </td>
                        <td className="px-4 py-4 text-slate-300">
                          {frame.timestamp_seconds === null
                            ? "N/A"
                            : `${frame.timestamp_seconds}s`}
                        </td>
                        <td className="px-4 py-4 text-slate-300">
                          {formatPercent(frame.final_score)}
                        </td>
                        <td className="px-4 py-4 text-slate-300">
                          {formatDecimal(frame.final_score)}
                        </td>
                        <td className="px-4 py-4">
                          <span
                            className={`inline-flex rounded-full border px-3 py-1 text-xs font-bold ${getRiskClassName(
                              frame.risk_level
                            )}`}
                          >
                            {getRiskLabel(frame.risk_level)}
                          </span>
                        </td>
                        <td className="rounded-r-xl px-4 py-4 text-slate-300">
                          {formatPercent(frame.confidence)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
        )}

        <section className="mt-6 rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
          <h2 className="text-xl font-bold">Model Predictions</h2>

          <div className="mt-5 overflow-x-auto">
            <table className="w-full min-w-[760px] border-separate border-spacing-y-2 text-left text-sm">
              <thead className="text-slate-400">
                <tr>
                  <th className="px-4 py-2">Model</th>
                  <th className="px-4 py-2">Version</th>
                  <th className="px-4 py-2">Raw Score</th>
                  <th className="px-4 py-2">Calibrated Score</th>
                  <th className="px-4 py-2">Label</th>
                  <th className="px-4 py-2">Target</th>
                </tr>
              </thead>

              <tbody>
                {data.model_predictions.length === 0 ? (
                  <tr>
                    <td
                      colSpan={6}
                      className="rounded-xl bg-slate-950 px-4 py-4 text-slate-400"
                    >
                      No model predictions available.
                    </td>
                  </tr>
                ) : (
                  data.model_predictions.map((prediction) => (
                    <tr key={prediction.id} className="bg-slate-950/70">
                      <td className="rounded-l-xl px-4 py-4 font-medium text-slate-200">
                        {prediction.model_name}
                      </td>
                      <td className="px-4 py-4 text-slate-300">
                        {prediction.model_version}
                      </td>
                      <td className="px-4 py-4 text-slate-300">
                        {formatPercent(prediction.raw_score)}
                      </td>
                      <td className="px-4 py-4 text-slate-300">
                        {formatPercent(prediction.calibrated_score)}
                      </td>
                      <td className="px-4 py-4 text-slate-300">
                        {prediction.prediction_label}
                      </td>
                      <td className="rounded-r-xl px-4 py-4 text-slate-300">
                        {prediction.target_region || "N/A"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="mt-6 rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
          <h2 className="text-xl font-bold">Forensic Signals</h2>

          <div className="mt-5 grid gap-4 md:grid-cols-3">
            {data.forensic_signals.length === 0 ? (
              <div className="rounded-xl border border-slate-800 bg-slate-950 p-5 text-slate-400">
                No forensic signals available.
              </div>
            ) : (
              data.forensic_signals.map((signal) => (
                <div
                  key={signal.id}
                  className="rounded-xl border border-slate-800 bg-slate-950 p-5"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-bold text-slate-200">
                      {signal.signal_value || signal.signal_type}
                    </p>

                    <span className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300">
                      {signal.signal_type}
                    </span>
                  </div>

                  <p className="mt-4 text-3xl font-extrabold">
                    {formatPercent(signal.risk_contribution)}
                  </p>

                  <p className="mt-3 text-sm leading-6 text-slate-400">
                    {signal.details?.description || "No description available."}
                  </p>

                  <p className="mt-4 text-xs uppercase tracking-wide text-slate-500">
                    Severity: {signal.details?.severity || "N/A"}
                  </p>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="mt-6 rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
          <h2 className="text-xl font-bold">IDs</h2>

          <div className="mt-5 grid gap-4 text-sm md:grid-cols-2">
            <div>
              <p className="text-slate-500">Job ID</p>
              <p className="mt-1 break-all text-slate-300">
                {data.job.job_id}
              </p>
            </div>

            <div>
              <p className="text-slate-500">Upload ID</p>
              <p className="mt-1 break-all text-slate-300">
                {data.job.upload_id}
              </p>
            </div>

            {data.result?.id && (
              <div>
                <p className="text-slate-500">Result ID</p>
                <p className="mt-1 break-all text-slate-300">
                  {data.result.id}
                </p>
              </div>
            )}

            <div>
              <p className="text-slate-500">Generated At</p>
              <p className="mt-1 text-slate-300">
                {formatDate(data.result?.created_at)}
              </p>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}``