import type { Metadata } from 'next'
import { Geist } from 'next/font/google'
import Link from 'next/link'
import './globals.css'
import { Providers } from './providers'

const geist = Geist({ subsets: ['latin'], variable: '--font-geist-sans' })

export const metadata: Metadata = {
  title: 'Enterprise RAG Agent',
  description: 'Interface de gestion et conversation pour votre knowledge base IA',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className={`${geist.variable} h-full antialiased`}>
      <body className="flex h-full flex-col bg-neutral-50 text-neutral-900">
        <Providers>
          <header className="shrink-0 border-b border-neutral-200 bg-white">
            <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
              <Link href="/chat" className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-md bg-neutral-900">
                  <svg className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <span className="text-sm font-semibold">RAG Agent</span>
              </Link>

              <nav className="flex items-center gap-1">
                <Link
                  href="/chat"
                  className="rounded-md px-3 py-1.5 text-sm text-neutral-600 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
                >
                  Chat
                </Link>
                <Link
                  href="/documents"
                  className="rounded-md px-3 py-1.5 text-sm text-neutral-600 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
                >
                  Documents
                </Link>
                <Link
                  href="/settings"
                  className="rounded-md px-3 py-1.5 text-sm text-neutral-600 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
                >
                  Paramètres
                </Link>
              </nav>
            </div>
          </header>

          <main className="flex flex-1 flex-col overflow-hidden">{children}</main>
        </Providers>
      </body>
    </html>
  )
}
