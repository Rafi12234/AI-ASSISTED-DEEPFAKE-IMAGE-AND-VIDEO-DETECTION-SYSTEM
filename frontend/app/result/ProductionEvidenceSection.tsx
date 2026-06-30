"use client";

import { Brain, Cpu, Eye, Fingerprint, Layers3 } from "lucide-react";

import type { ProductionEvidenceResponse } from "@/types/aiModels";
import FaceEvidenceSection from "./FaceEvidenceSection";

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "N/A";
  }

  return `${Math.round(value * 100)}%`;
}

function formatValue(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") {
    return "N/A";
  }

  return String(value);
}

function getBadgeStyle(value?: string | null) {
  switch (value) {
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

export default function ProductionEvidenceSection({
  evidence,
}: {
  evidence: ProductionEvidenceResponse;
}) {
  return (
    <section className="mt-6 rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
      <div className="flex items-center gap-3">
        <Layers3 className="h-6 w-6 text-slate-300" />
        <div>
          <h2 className="text-xl font-bold">Production AI Evidence</h2>
          <p className="mt-1 text-sm text-slate-400">
            Model-level, forensic-level, and future face/video/audio evidence.
          </p>
        </div>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-4">
        <div className="rounded-xl border border-slate-800 bg-slate-950 p-5">
          <p className="text-sm text-slate-500">Engine</p>
          <p className="mt-2 break-words text-sm font-bold text-slate-200">
            {formatValue(evidence.summary.engine)}
          </p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950 p-5">
          <p className="text-sm text-slate-500">Pipeline</p>
          <p className="mt-2 break-words text-sm font-bold text-slate-200">
            {formatValue(evidence.summary.pipeline_version)}
          </p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950 p-5">
          <p className="text-sm text-slate-500">Model Evidence</p>
          <p className="mt-2 text-3xl font-extrabold">
            {evidence.model_evidence.length}
          </p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950 p-5">
          <p className="text-sm text-slate-500">Forensic Evidence</p>
          <p className="mt-2 text-3xl font-extrabold">
            {evidence.forensic_evidence.length}
          </p>
        </div>
      </div>

      {evidence.production_pipeline?.note && (
        <div className="mt-5 rounded-xl border border-blue-500/30 bg-blue-500/10 p-4 text-sm leading-6 text-blue-100">
          {evidence.production_pipeline.note}
        </div>
      )}

      <div className="mt-6">
        <div className="flex items-center gap-3">
          <Brain className="h-5 w-5 text-slate-300" />
          <h3 className="text-lg font-bold">Model Evidence Breakdown</h3>
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[900px] border-separate border-spacing-y-2 text-left text-sm">
            <thead className="text-slate-400">
              <tr>
                <th className="px-4 py-2">Model</th>
                <th className="px-4 py-2">Version</th>
                <th className="px-4 py-2">Type</th>
                <th className="px-4 py-2">Input</th>
                <th className="px-4 py-2">Score</th>
                <th className="px-4 py-2">Confidence</th>
                <th className="px-4 py-2">Device</th>
                <th className="px-4 py-2">Latency</th>
              </tr>
            </thead>

            <tbody>
              {evidence.model_evidence.length === 0 ? (
                <tr>
                  <td
                    colSpan={8}
                    className="rounded-xl bg-slate-950 px-4 py-5 text-slate-400"
                  >
                    No production model evidence stored yet.
                  </td>
                </tr>
              ) : (
                evidence.model_evidence.map((item, index) => (
                  <tr
                    key={`${item.model_name}-${item.model_version}-${index}`}
                    className="bg-slate-950/70"
                  >
                    <td className="rounded-l-xl px-4 py-4 font-semibold text-slate-200">
                      {item.model_name}
                    </td>
                    <td className="px-4 py-4 text-slate-300">
                      {item.model_version}
                    </td>
                    <td className="px-4 py-4 text-slate-300">
                      {item.model_type}
                    </td>
                    <td className="px-4 py-4 text-slate-300">
                      {item.input_type}
                    </td>
                    <td className="px-4 py-4">
                      <span
                        className={`inline-flex rounded-full border px-3 py-1 text-xs font-bold ${getBadgeStyle(
                          evidence.summary.risk_level
                        )}`}
                      >
                        {formatPercent(item.score)}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-slate-300">
                      {formatPercent(item.confidence)}
                    </td>
                    <td className="px-4 py-4 text-slate-300">
                      <span className="inline-flex items-center gap-2">
                        <Cpu className="h-4 w-4 text-slate-500" />
                        {item.device}
                      </span>
                    </td>
                    <td className="rounded-r-xl px-4 py-4 text-slate-300">
                      {item.latency_ms === null ? "N/A" : `${item.latency_ms} ms`}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mt-6">
        <div className="flex items-center gap-3">
          <Fingerprint className="h-5 w-5 text-slate-300" />
          <h3 className="text-lg font-bold">Forensic Evidence Breakdown</h3>
        </div>

        <div className="mt-4 grid gap-4 md:grid-cols-3">
          {evidence.forensic_evidence.length === 0 ? (
            <div className="rounded-xl border border-slate-800 bg-slate-950 p-5 text-slate-400">
              No forensic evidence available.
            </div>
          ) : (
            evidence.forensic_evidence.map((item, index) => (
              <div
                key={`${item.signal_type}-${item.signal_name}-${index}`}
                className="rounded-xl border border-slate-800 bg-slate-950 p-5"
              >
                <div className="flex items-start justify-between gap-3">
                  <p className="font-bold text-slate-200">
                    {item.signal_name || item.signal_type}
                  </p>

                  <span className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300">
                    {item.signal_type}
                  </span>
                </div>

                <p className="mt-4 text-3xl font-extrabold">
                  {formatPercent(item.score)}
                </p>

                <p className="mt-3 text-sm leading-6 text-slate-400">
                  {item.description || "No description available."}
                </p>

                <p className="mt-4 text-xs uppercase tracking-wide text-slate-500">
                  Severity: {item.severity || "N/A"}
                </p>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-950 p-5">
          <div className="flex items-center gap-2">
            <Eye className="h-5 w-5 text-slate-400" />
            <p className="font-bold text-slate-200">Face Evidence</p>
          </div>
          <p className="mt-3 text-3xl font-extrabold">
            {evidence.face_evidence.length}
          </p>
          <p className="mt-2 text-sm text-slate-500">
            Will be populated after face detection chunks.
          </p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950 p-5">
          <div className="flex items-center gap-2">
            <Eye className="h-5 w-5 text-slate-400" />
            <p className="font-bold text-slate-200">Frame Evidence</p>
          </div>
          <p className="mt-3 text-3xl font-extrabold">
            {evidence.frame_evidence.length}
          </p>
          <p className="mt-2 text-sm text-slate-500">
            Video sampled-frame evidence.
          </p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950 p-5">
          <div className="flex items-center gap-2">
            <Eye className="h-5 w-5 text-slate-400" />
            <p className="font-bold text-slate-200">Audio Evidence</p>
          </div>
          <p className="mt-3 text-3xl font-extrabold">
            {evidence.audio_evidence ? 1 : 0}
          </p>
          <p className="mt-2 text-sm text-slate-500">
            Will be populated after audio/AV sync chunks.
          </p>
        </div>
        {evidence.face_evidence.length > 0 && (
  <FaceEvidenceSection faceEvidence={evidence.face_evidence} />
)}
      </div>
    </section>
  );
}