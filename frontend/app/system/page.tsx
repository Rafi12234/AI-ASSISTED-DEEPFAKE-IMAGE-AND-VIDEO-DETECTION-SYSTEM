"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertCircle,
  ArrowLeft,
  Brain,
  CheckCircle2,
  Database,
  HardDrive,
  RefreshCw,
  Server,
  Wifi,
} from "lucide-react";

import { getSystemHealth } from "@/lib/system";
import type { ServiceHealth, SystemHealthResponse } from "@/types/system";

type ServiceCard = {
  key: string;
  title: string;
  description: string;
  data: ServiceHealth;
};

function getStatusStyle(status: string) {
  if (status === "ok") {
    return "border-emerald-500/40 bg-emerald-500/10 text-emerald-300";
  }

  if (status === "degraded") {
    return "border-yellow-500/40 bg-yellow-500/10 text-yellow-300";
  }

  return "border-red-500/40 bg-red-500/10 text-red-300";
}

function StatusIcon({
  status,
  className,
}: {
  status: string;
  className: string;
}) {
  if (status === "ok") {
    return <CheckCircle2 className={className} />;
  }

  return <AlertCircle className={className} />;
}

function ServiceMainIcon({
  serviceKey,
  className,
}: {
  serviceKey: string;
  className: string;
}) {
  switch (serviceKey) {
    case "backend_api":
      return <Server className={className} />;

    case "database":
      return <Database className={className} />;

    case "redis":
      return <Wifi className={className} />;

    case "minio":
      return <HardDrive className={className} />;

    case "ai_service":
      return <Brain className={className} />;

    default:
      return <Activity className={className} />;
  }
}

export default function SystemPage() {
  const [data, setData] = useState<SystemHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  async function loadHealth(isRefresh = false) {
    try {
      setError("");

      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      const result = await getSystemHealth();
      setData(result);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load system health."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadHealth(false);
    }, 0);

    return () => {
      window.clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const serviceCards = useMemo<ServiceCard[]>(() => {
    if (!data) {
      return [];
    }

    return [
      {
        key: "backend_api",
        title: "Backend API",
        description: "FastAPI backend on port 8000",
        data: data.services.backend_api,
      },
      {
        key: "database",
        title: "PostgreSQL",
        description: "Main relational database",
        data: data.services.database,
      },
      {
        key: "redis",
        title: "Redis Queue",
        description: "Background job queue",
        data: data.services.redis,
      },
      {
        key: "minio",
        title: "MinIO Storage",
        description: "Raw uploads and report storage",
        data: data.services.minio,
      },
      {
        key: "ai_service",
        title: "AI Service",
        description: "Image/video analysis service on port 8010",
        data: data.services.ai_service,
      },
    ];
  }, [data]);

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-950 px-6 py-10 text-white">
        <div className="mx-auto max-w-6xl rounded-2xl border border-slate-800 bg-slate-900/70 p-8">
          <div className="flex items-center gap-3 text-slate-300">
            <RefreshCw className="h-5 w-5 animate-spin" />
            Loading system health...
          </div>
        </div>
      </main>
    );
  }

  if (error) {
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
            <h1 className="text-2xl font-bold text-red-100">
              System Health Error
            </h1>

            <p className="mt-3 text-red-100">{error}</p>

            <button
              onClick={() => void loadHealth(true)}
              className="mt-6 rounded-xl bg-white px-5 py-3 text-sm font-bold text-slate-950 hover:bg-slate-200"
            >
              Try Again
            </button>
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
              System Health
            </h1>

            <p className="mt-2 text-slate-400">
              Monitor backend, database, queue, storage, and AI service status.
            </p>
          </div>

          <button
            onClick={() => void loadHealth(true)}
            disabled={refreshing}
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-5 py-3 text-sm font-bold text-white hover:bg-slate-800 disabled:opacity-60"
          >
            <RefreshCw
              className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
            />
            Refresh
          </button>
        </div>

        <section
          className={`mb-6 rounded-2xl border p-6 ${getStatusStyle(
            data.status
          )}`}
        >
          <div className="flex items-center gap-3">
            <StatusIcon status={data.status} className="h-7 w-7" />

            <div>
              <p className="text-sm font-medium opacity-80">Overall Status</p>
              <h2 className="text-2xl font-extrabold uppercase">
                {data.status}
              </h2>
            </div>
          </div>
        </section>

        <section className="grid gap-6 md:grid-cols-2">
          {serviceCards.map((service) => (
            <div
              key={service.key}
              className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                  <ServiceMainIcon
                    serviceKey={service.key}
                    className="h-6 w-6 text-slate-300"
                  />

                  <div>
                    <h2 className="text-xl font-bold">{service.title}</h2>
                    <p className="mt-1 text-sm text-slate-500">
                      {service.description}
                    </p>
                  </div>
                </div>

                <span
                  className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-bold uppercase ${getStatusStyle(
                    service.data.status
                  )}`}
                >
                  <StatusIcon status={service.data.status} className="h-4 w-4" />
                  {service.data.status}
                </span>
              </div>

              <p className="mt-5 text-sm leading-6 text-slate-300">
                {service.data.message || "No message available."}
              </p>

              {service.data.engine && (
                <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950 p-4 text-sm">
                  <p className="text-slate-500">Engine</p>
                  <p className="mt-1 font-semibold text-slate-200">
                    {service.data.engine}
                  </p>
                </div>
              )}

              {service.data.supported_media &&
                service.data.supported_media.length > 0 && (
                  <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950 p-4 text-sm">
                    <p className="text-slate-500">Supported Media</p>
                    <p className="mt-1 font-semibold text-slate-200">
                      {service.data.supported_media.join(", ")}
                    </p>
                  </div>
                )}
            </div>
          ))}
        </section>

        <section className="mt-6 rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
          <div className="flex items-center gap-3">
            <Activity className="h-6 w-6 text-slate-300" />
            <h2 className="text-xl font-bold">How to start all services</h2>
          </div>

          <pre className="mt-5 overflow-x-auto rounded-xl bg-slate-950 p-4 text-sm text-slate-200">
{`cd "D:\\All Projects\\Deepfake-Detection-System\\Deepfake-Detection-System"
scripts\\run-all-dev.bat`}
          </pre>
        </section>
      </div>
    </main>
  );
}