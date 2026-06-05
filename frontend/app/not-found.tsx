import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-neutral-100">
        <span className="text-2xl font-bold text-neutral-400">404</span>
      </div>
      <div>
        <h2 className="text-lg font-semibold text-neutral-900">Page introuvable</h2>
        <p className="mt-1 text-sm text-neutral-500">Cette page n&apos;existe pas ou a été déplacée.</p>
      </div>
      <Link
        href="/chat"
        className="rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-neutral-700"
      >
        Retour au chat
      </Link>
    </div>
  )
}
