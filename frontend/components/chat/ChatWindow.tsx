'use client'
import { useEffect, useRef } from 'react'
import { useSessionStore } from '@/lib/store/session'
import { MessageBubble } from './MessageBubble'
import { Spinner } from '@/components/ui/spinner'

interface ChatWindowProps {
  isLoading: boolean
}

export function ChatWindow({ isLoading }: ChatWindowProps) {
  const messages = useSessionStore((s) => s.messages)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
        <div className="rounded-full bg-neutral-100 p-4">
          <svg className="h-8 w-8 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        </div>
        <p className="text-sm font-medium text-neutral-700">Commencez la conversation</p>
        <p className="text-xs text-neutral-400 max-w-xs">
          Posez une question — {"l'"}agent cherchera automatiquement dans la base de documents.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-4 py-4">
      {messages.map((msg, i) => (
        <MessageBubble key={i} message={msg} />
      ))}
      {isLoading && (
        <div className="flex justify-start">
          <div className="flex items-center gap-2 rounded-2xl rounded-bl-sm bg-neutral-100 px-4 py-3">
            <Spinner size="sm" />
            <span className="text-xs text-neutral-500">{"L'"}agent réfléchit…</span>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}
