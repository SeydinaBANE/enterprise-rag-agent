'use client'
import { ApiKeyGuard } from '@/components/shared/ApiKeyGuard'
import { ChatWindow } from '@/components/chat/ChatWindow'
import { InputBar } from '@/components/chat/InputBar'
import { useChat } from '@/hooks/useChat'
import { useSessionStore } from '@/lib/store/session'

function ChatPage() {
  const { mutate, isPending } = useChat()
  const resetSession = useSessionStore((s) => s.resetSession)

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <ChatWindow isLoading={isPending} />
      <InputBar
        onSend={(msg) => mutate(msg)}
        onNewSession={resetSession}
        isLoading={isPending}
      />
    </div>
  )
}

export default function ChatRoute() {
  return (
    <ApiKeyGuard>
      <ChatPage />
    </ApiKeyGuard>
  )
}
