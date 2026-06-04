import { apiFetch } from './client'
import type { ChatRequest, ChatResponse } from '@/types/api'

export function postChat(req: ChatRequest): Promise<ChatResponse> {
  return apiFetch<ChatResponse>('/chat', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}
