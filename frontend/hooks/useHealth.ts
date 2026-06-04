'use client'
import { useQuery } from '@tanstack/react-query'
import { useConfigStore } from '@/lib/store/config'
import type { HealthResponse } from '@/types/api'

export function useHealth() {
  const apiUrl = useConfigStore((s) => s.apiUrl)

  return useQuery<HealthResponse>({
    queryKey: ['health', apiUrl],
    queryFn: async () => {
      const res = await fetch(`${apiUrl}/health`)
      if (!res.ok) throw new Error('Health check failed')
      return res.json() as Promise<HealthResponse>
    },
    refetchInterval: 30_000,
    staleTime: 20_000,
  })
}
