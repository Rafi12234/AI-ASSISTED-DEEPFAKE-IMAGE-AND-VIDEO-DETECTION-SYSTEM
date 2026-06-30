"use client";

import { Box, Brain, Eye, ScanFace } from "lucide-react";

import type { ProductionFaceEvidence } from "@/types/aiModels";

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

function getFaceScoreStyle(score?: number | null) {
  if (score === null || score === undefined) {
    return "border-slate-500/40 bg-slate-500/10 text-slate-300";
  }

  if (score >= 0.8) {
    return "border-red-500/40 bg-red-500/10 text-red-300";
  }

  if (score >= 0.61) {
    return "border-orange-500/40 bg-orange-500/10 text-orange-300";
  }

  if (score >= 0.33) {
    return "border-yellow-500/40 bg-yellow-500/10 text-yellow-300";
  }

  return "border-emerald-500/40 bg-emerald-500/10 text-emerald-300";
}

function getBBoxText(face: ProductionFaceEvidence) {
  const bbox = face.bbox;

  if (!bbox) {
    return "N/A";
  }

  if (Array.isArray(bbox)) {
    const [x, y, width, height] = bbox;

    return `x=${x}, y=${y}, w=${width}, h=${height}`;
  }

  return `x=${bbox.x ?? "N/A"}, y=${bbox.y ?? "N/A"}, w=${
    bbox.width ?? "N/A"
  }, h=${bbox.height ?? "N/A"}`;
}

function getPaddedBBoxText(face: ProductionFaceEvidence) {
  const bbox = face.bbox;

  if (!bbox || Array.isArray(bbox)) {
    return "N/A";
  }

  return `x=${bbox.padded_x ?? "N/A"}, y=${bbox.padded_y ?? "N/A"}, w=${
    bbox.padded_width ?? "N/A"
  }, h=${bbox.padded_height ?? "N/A"}`;
}

function getDetailsValue(
  details: Record<string, unknown> | undefined,
  key: string
) {
  if (!details) {
    return null;
  }

  const value = details[key];

  if (typeof value === "string" || typeof value === "number") {
    return value;
  }

  return null;
}

export default function FaceEvidenceSection({
  faceEvidence,
}: {
  faceEvidence: ProductionFaceEvidence[];
}) {
  if (faceEvidence.length === 0) {
    return (
      <section className="mt-6 rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
        <div className="flex items-center gap-3">
          <ScanFace className="h-6 w-6 text-slate-300" />
          <div>
            <h2 className="text-xl font-bold">Face Evidence</h2>
            <p className="mt-1 text-sm text-slate-400">
              No face-level model evidence was stored for this result.
            </p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="mt-6 rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
      <div className="flex items-center gap-3">
        <ScanFace className="h-6 w-6 text-slate-300" />
        <div>
          <h2 className="text-xl font-bold">Face Evidence</h2>
          <p className="mt-1 text-sm text-slate-400">
            Face-level evidence generated from detected face crops and the
            current face-crop baseline model.
          </p>
        </div>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-950 p-5">
          <div className="flex items-center gap-2">
            <Eye className="h-5 w-5 text-slate-400" />
            <p className="text-sm text-slate-500">Detected Face Evidence</p>
          </div>
          <p className="mt-3 text-3xl font-extrabold">
            {faceEvidence.length}
          </p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950 p-5">
          <div className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-slate-400" />
            <p className="text-sm text-slate-500">Highest Face Score</p>
          </div>
          <p className="mt-3 text-3xl font-extrabold">
            {formatPercent(
              Math.max(
                ...faceEvidence.map((item) => item.face_score ?? 0)
              )
            )}
          </p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950 p-5">
          <div className="flex items-center gap-2">
            <Box className="h-5 w-5 text-slate-400" />
            <p className="text-sm text-slate-500">Model Used</p>
          </div>
          <p className="mt-3 break-words text-sm font-bold text-slate-200">
            {formatValue(
              faceEvidence[0]?.model_name ||
                getDetailsValue(faceEvidence[0]?.details, "model_name")
            )}
          </p>
        </div>
      </div>

      <div className="mt-6 grid gap-4">
        {faceEvidence.map((face, index) => {
          const modelName =
            face.model_name ||
            getDetailsValue(face.details, "model_name");

          const modelVersion =
            face.model_version ||
            getDetailsValue(face.details, "model_version");

          const predictedLabel =
            face.predicted_label ||
            getDetailsValue(face.details, "predicted_label");

          const qualityScore =
            face.quality_score ??
            (typeof getDetailsValue(face.details, "quality_score") === "number"
              ? Number(getDetailsValue(face.details, "quality_score"))
              : null);

          return (
            <div
              key={`${face.face_id}-${index}`}
              className="rounded-xl border border-slate-800 bg-slate-950 p-5"
            >
              <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500">
                    Face #{index + 1}
                  </p>

                  <h3 className="mt-1 break-all text-base font-bold text-slate-100">
                    {face.face_id}
                  </h3>
                </div>

                <span
                  className={`w-fit rounded-full border px-3 py-1 text-xs font-bold ${getFaceScoreStyle(
                    face.face_score
                  )}`}
                >
                  Face Score {formatPercent(face.face_score)}
                </span>
              </div>

              <div className="mt-5 grid gap-4 md:grid-cols-4">
                <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
                  <p className="text-xs text-slate-500">Predicted Label</p>
                  <p className="mt-2 font-bold text-slate-200">
                    {formatValue(predictedLabel)}
                  </p>
                </div>

                <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
                  <p className="text-xs text-slate-500">Confidence</p>
                  <p className="mt-2 font-bold text-slate-200">
                    {formatPercent(face.detection_confidence)}
                  </p>
                </div>

                <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
                  <p className="text-xs text-slate-500">Crop Quality</p>
                  <p className="mt-2 font-bold text-slate-200">
                    {formatPercent(qualityScore)}
                  </p>
                </div>

                <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
                  <p className="text-xs text-slate-500">Frame</p>
                  <p className="mt-2 font-bold text-slate-200">
                    {face.frame_number === null ||
                    face.frame_number === undefined
                      ? "Image"
                      : face.frame_number}
                  </p>
                </div>
              </div>

              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
                  <p className="text-xs text-slate-500">Bounding Box</p>
                  <p className="mt-2 break-words text-sm font-semibold text-slate-200">
                    {getBBoxText(face)}
                  </p>
                </div>

                <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
                  <p className="text-xs text-slate-500">Padded Crop Box</p>
                  <p className="mt-2 break-words text-sm font-semibold text-slate-200">
                    {getPaddedBBoxText(face)}
                  </p>
                </div>
              </div>

              <div className="mt-5 rounded-lg border border-slate-800 bg-slate-900/60 p-4">
                <p className="text-xs text-slate-500">Model</p>
                <p className="mt-2 break-words text-sm font-semibold text-slate-200">
                  {formatValue(modelName)} / {formatValue(modelVersion)}
                </p>
              </div>

              <div className="mt-5 rounded-lg border border-slate-800 bg-slate-900/60 p-4">
                <p className="text-xs text-slate-500">Crop Path</p>
                <p className="mt-2 break-all text-xs leading-6 text-slate-300">
                  {formatValue(face.crop_path)}
                </p>

                <p className="mt-3 text-xs leading-5 text-slate-500">
                  This is currently a local AI-worker file path. A later chunk
                  can add secure crop preview/download from the backend.
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}