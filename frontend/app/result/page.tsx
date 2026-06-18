import { Suspense } from "react";

import ResultClient from "./ResultClient";

export default function ResultPage() {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen bg-slate-950 px-6 py-10 text-white">
          <div className="mx-auto max-w-6xl">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-8">
              Loading result page...
            </div>
          </div>
        </main>
      }
    >
      <ResultClient />
    </Suspense>
  );
}