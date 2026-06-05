import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface ConfigState {
  apiKey: string
  apiUrl: string
  setApiKey: (key: string) => void
  setApiUrl: (url: string) => void
}

export const useConfigStore = create<ConfigState>()(
  persist(
    (set) => ({
      apiKey: '',
      apiUrl: process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000',
      setApiKey: (apiKey) => set({ apiKey }),
      setApiUrl: (apiUrl) => set({ apiUrl }),
    }),
    { name: 'rag-config' },
  ),
)
