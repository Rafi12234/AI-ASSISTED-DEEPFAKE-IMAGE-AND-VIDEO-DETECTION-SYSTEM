import Link from "next/link";
import { ShieldCheck, Upload, SearchCheck, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-[#0D0F14] text-white">
      <section className="mx-auto flex min-h-screen max-w-6xl flex-col items-center justify-center px-6 py-20 text-center">
        <div className="mb-6 inline-flex items-center rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-zinc-300">
          <ShieldCheck className="mr-2 h-4 w-4" />
          AI-assisted deepfake image and video detection
        </div>

        <h1 className="max-w-4xl text-4xl font-bold tracking-tight md:text-6xl">
          Detect suspicious AI-generated media with risk scoring and evidence.
        </h1>

        <p className="mt-6 max-w-2xl text-lg leading-8 text-zinc-400">
          Upload images or videos, analyze forensic and AI signals, view confidence
          scores, and send high-risk cases for human review.
        </p>

        <div className="mt-10 flex flex-col gap-4 sm:flex-row">
          <Button asChild size="lg">
            <Link href="/upload">
              <Upload className="mr-2 h-5 w-5" />
              Start Analysis
            </Link>
          </Button>

          <Button asChild size="lg" variant="outline">
            <Link href="/dashboard">View Dashboard</Link>
          </Button>
        </div>

        <div className="mt-16 grid w-full gap-6 md:grid-cols-3">
          <Card className="border-white/10 bg-white/5 text-white">
            <CardContent className="p-6 text-left">
              <SearchCheck className="mb-4 h-8 w-8" />
              <h3 className="text-xl font-semibold">AI + forensic signals</h3>
              <p className="mt-2 text-sm text-zinc-400">
                Combines model scores, metadata, frame analysis, and suspicious
                artifact detection.
              </p>
            </CardContent>
          </Card>

          <Card className="border-white/10 bg-white/5 text-white">
            <CardContent className="p-6 text-left">
              <ShieldCheck className="mb-4 h-8 w-8" />
              <h3 className="text-xl font-semibold">Risk-based result</h3>
              <p className="mt-2 text-sm text-zinc-400">
                Shows likely authentic, uncertain, suspicious, or high-risk
                instead of claiming 100% certainty.
              </p>
            </CardContent>
          </Card>

          <Card className="border-white/10 bg-white/5 text-white">
            <CardContent className="p-6 text-left">
              <Lock className="mb-4 h-8 w-8" />
              <h3 className="text-xl font-semibold">Privacy-first design</h3>
              <p className="mt-2 text-sm text-zinc-400">
                Local-first architecture with private storage, audit logs, and
                human review for sensitive cases.
              </p>
            </CardContent>
          </Card>
        </div>
      </section>
    </main>
  );
}