'use client'
import { useEffect, useSyncExternalStore } from 'react'
import { useRouter } from 'next/navigation'
import { useConfigStore } from '@/lib/store/config'
import { Spinner } from '@/components/ui/spinner'

function useIsHydrated(): boolean {
  return useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  )
}

interface ApiKeyGuardProps {
  children: React.ReactNode
}

export function ApiKeyGuard({ children }: ApiKeyGuardProps) {
  const apiKey = useConfigStore((s) => s.apiKey)
  const router = useRouter()
  const hydrated = useIsHydrated()

  useEffect(() => {
    if (hydrated && !apiKey) {
      router.push('/settings')
    }
  }, [hydrated, apiKey, router])

  if (!hydrated) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="lg" />
      </div>
    )
  }

  if (!apiKey) return null

  return <>{children}</>
}
