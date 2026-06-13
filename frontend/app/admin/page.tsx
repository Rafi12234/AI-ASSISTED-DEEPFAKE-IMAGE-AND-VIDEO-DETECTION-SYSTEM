"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { clearAuth, getCurrentUser, getStoredToken } from "@/lib/auth";
import type { AuthUser } from "@/types/auth";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function AdminPage() {
  const router = useRouter();

  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    async function loadUser() {
      const token = getStoredToken();

      if (!token) {
        router.push("/login");
        return;
      }

      try {
        const currentUser = await getCurrentUser();
        setUser(currentUser);

        if (currentUser.role === "admin" || currentUser.role === "reviewer") {
          setAllowed(true);
        }
      } catch {
        clearAuth();
        router.push("/login");
      } finally {
        setLoading(false);
      }
    }

    loadUser();
  }, [router]);

  function handleLogout() {
    clearAuth();
    router.push("/login");
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-[#0D0F14] px-6 py-16 text-white">
        <div className="mx-auto max-w-5xl">
          <p className="text-zinc-400">Checking admin access...</p>
        </div>
      </main>
    );
  }

  if (!allowed) {
    return (
      <main className="min-h-screen bg-[#0D0F14] px-6 py-16 text-white">
        <div className="mx-auto max-w-5xl">
          <Card className="border-red-500/30 bg-red-500/10 text-white">
            <CardContent className="p-8">
              <h1 className="text-2xl font-bold">Access Denied</h1>
              <p className="mt-3 text-red-100">
                Your account does not have reviewer or admin permission.
              </p>

              <Button
                className="mt-6"
                variant="outline"
                onClick={() => router.push("/dashboard")}
              >
                Go to Dashboard
              </Button>
            </CardContent>
          </Card>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#0D0F14] px-6 py-16 text-white">
      <div className="mx-auto max-w-5xl">
        <div className="flex flex-col justify-between gap-6 md:flex-row md:items-center">
          <div>
            <h1 className="text-3xl font-bold">Admin Review Dashboard</h1>
            <p className="mt-3 text-zinc-400">
              Logged in as {user?.email}
            </p>
            <p className="mt-1 text-sm text-zinc-500">
              Role: {user?.role}
            </p>
          </div>

          <Button variant="outline" onClick={handleLogout}>
            Logout
          </Button>
        </div>

        <Card className="mt-10 border-white/10 bg-white/5 text-white">
          <CardContent className="p-8">
            <h2 className="text-xl font-semibold">Review Queue</h2>
            <p className="mt-3 text-zinc-400">
              Suspicious and high-risk cases will appear here after the analysis
              system is completed.
            </p>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}