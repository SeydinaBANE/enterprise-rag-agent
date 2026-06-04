import { useConfigStore } from '@/lib/store/config'

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const { apiKey, apiUrl } = useConfigStore.getState()

  const headers: Record<string, string> = {
    'X-API-Key': apiKey,
    ...(options?.headers as Record<string, string>),
  }

  if (!(options?.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }

  const res = await fetch(`${apiUrl}${path}`, { ...options, headers })

  if (res.status === 401) throw new ApiError(401, 'Clé API invalide — vérifiez vos paramètres')
  if (res.status === 429) throw new ApiError(429, 'Trop de requêtes — réessayez dans une minute')
  if (res.status === 413) throw new ApiError(413, 'Fichier trop volumineux (max 50 MB)')

  if (!res.ok) {
    let message = `Erreur ${res.status}`
    try {
      const body = (await res.json()) as { detail?: string }
      if (typeof body.detail === 'string') message = body.detail
    } catch {
      // ignore parse errors
    }
    throw new ApiError(res.status, message)
  }

  return res.json() as Promise<T>
}
