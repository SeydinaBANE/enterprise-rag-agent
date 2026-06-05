'use client'

export default function GlobalError({
  unstable_retry,
}: {
  error: Error & { digest?: string }
  unstable_retry: () => void
}) {
  return (
    <html lang="fr">
      <body className="flex min-h-screen flex-col items-center justify-center gap-4 bg-neutral-50 p-8 text-center font-sans">
        <h2 className="text-lg font-semibold text-neutral-900">Une erreur critique est survenue</h2>
        <button
          onClick={() => unstable_retry()}
          className="rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white"
        >
          Réessayer
        </button>
      </body>
    </html>
  )
}
