'use client'
import { useMutation } from '@tanstack/react-query'
import { postChat } from '@/lib/api/chat'
import { useSessionStore } from '@/lib/store/session'
import type { ChatResponse } from '@/types/api'

export function useChat() {
  const { sessionId, addMessage } = useSessionStore()

  return useMutation<ChatResponse, Error, string>({
    mutationFn: (message: string) => postChat({ message, session_id: sessionId }),
    onMutate: (message) => {
      addMessage({ role: 'user', content: message })
    },
    onSuccess: (data) => {
      addMessage({
        role: 'assistant',
        content: data.answer,
        sources: data.sources,
        used_retrieval: data.used_retrieval,
        latency_ms: data.latency_ms,
      })
    },
  })
}
