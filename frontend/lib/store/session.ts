import { create } from 'zustand'
import type { ChatMessage } from '@/types/api'

interface SessionState {
  sessionId: string
  messages: ChatMessage[]
  addMessage: (msg: ChatMessage) => void
  resetSession: () => void
}

export const useSessionStore = create<SessionState>()((set) => ({
  sessionId: crypto.randomUUID(),
  messages: [],
  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
  resetSession: () => set({ sessionId: crypto.randomUUID(), messages: [] }),
}))
