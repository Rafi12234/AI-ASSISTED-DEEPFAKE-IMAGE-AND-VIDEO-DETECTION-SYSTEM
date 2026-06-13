"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { LogOut, Upload } from "lucide-react";

import { clearAuth, getCurrentUser, getStoredToken } from "@/lib/auth";
import { getMyUploads } from "@/lib/uploads";
import type { AuthUser } from "@/types/auth";
import type { UploadDetail } from "@/types/upload";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

function formatBytes(bytes: number) {
  const mb = bytes / (1024 * 1024);
  return `${mb.toFixed(2)} MB`;
}

export default function DashboardPage() {
  const router = useRouter();

  const [user, setUser] = useState<AuthUser | null>(null);
  const [uploads, setUploads] = useState<UploadDetail[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDashboard() {
      const token = getStoredToken();

      if (!token) {
        router.push("/login");
        return;
      }

      try {
        const currentUser = await getCurrentUser();
        setUser(currentUser);

        const uploadList = await getMyUploads();
        setUploads(uploadList);
      } catch {
        clearAuth();
        router.push("/login");
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, [router]);

  function handleLogout() {
    clearAuth();
    router.push("/login");
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-[#0D0F14] px-6 py-16 text-white">
        <div className="mx-auto max-w-5xl">
          <p className="text-zinc-400">Loading dashboard...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#0D0F14] px-6 py-16 text-white">
      <div className="mx-auto max-w-5xl">
        <div className="flex flex-col justify-between gap-6 md:flex-row md:items-center">
          <div>
            <h1 className="text-3xl font-bold">User Dashboard</h1>
            <p className="mt-3 text-zinc-400">Welcome, {user?.email}</p>
            <p className="mt-1 text-sm text-zinc-500">Role: {user?.role}</p>
          </div>

          <div className="flex gap-3">
            <Button asChild>
              <Link href="/upload">
                <Upload className="mr-2 h-4 w-4" />
                Upload Media
              </Link>
            </Button>

            <Button variant="outline" onClick={handleLogout}>
              <LogOut className="mr-2 h-4 w-4" />
              Logout
            </Button>
          </div>
        </div>

        <Card className="mt-10 border-white/10 bg-white/5 text-white">
          <CardContent className="p-8">
            <h2 className="text-xl font-semibold">Upload History</h2>

            {uploads.length === 0 ? (
              <p className="mt-3 text-zinc-400">
                You have not uploaded any media yet.
              </p>
            ) : (
              <div className="mt-6 space-y-4">
                {uploads.map((upload) => (
                  <div
                    key={upload.id}
                    className="rounded-xl border border-white/10 bg-black/20 p-4"
                  >
                    <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
                      <div>
                        <h3 className="font-semibold">
                          {upload.original_filename}
                        </h3>
                        <p className="mt-1 text-sm text-zinc-400">
                          {upload.mime_type} • {formatBytes(upload.file_size_bytes)}
                        </p>
                        <p className="mt-1 text-xs text-zinc-500">
                          Uploaded:{" "}
                          {new Date(upload.created_at).toLocaleString()}
                        </p>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        <Badge variant="secondary">{upload.file_type}</Badge>
                        <Badge variant="secondary">
                          {upload.upload_status}
                        </Badge>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </main>
  );
}