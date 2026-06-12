export default function UploadPage() {
  return (
    <main className="min-h-screen bg-[#0D0F14] px-6 py-16 text-white">
      <div className="mx-auto max-w-3xl">
        <h1 className="text-3xl font-bold">Upload Media</h1>
        <p className="mt-3 text-zinc-400">
          Upload an image or video for AI-assisted deepfake analysis.
        </p>

        <div className="mt-10 rounded-2xl border border-dashed border-white/20 bg-white/5 p-10 text-center">
          <p className="text-lg font-medium">Upload box will be added in Chunk 5</p>
          <p className="mt-2 text-sm text-zinc-400">
            For now, this page confirms that frontend routing is working.
          </p>
        </div>
      </div>
    </main>
  );
}