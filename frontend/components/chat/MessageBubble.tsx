import { Badge } from '@/components/ui/badge'
import { SourcePanel } from './SourcePanel'
import { cn } from '@/lib/utils'
import type { ChatMessage } from '@/types/api'

interface MessageBubbleProps {
  message: ChatMessage
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex w-full', isUser ? 'justify-end' : 'justify-start')}>
      <div className={cn('max-w-[80%] space-y-1', isUser ? 'items-end' : 'items-start')}>
        <div
          className={cn(
            'rounded-2xl px-4 py-2.5 text-sm leading-relaxed',
            isUser
              ? 'bg-neutral-900 text-white rounded-br-sm'
              : 'bg-neutral-100 text-neutral-900 rounded-bl-sm',
          )}
        >
          {message.content}
        </div>

        {!isUser && (
          <div className="flex flex-wrap items-center gap-1.5 px-1">
            {message.used_retrieval !== undefined && (
              <Badge variant={message.used_retrieval ? 'blue' : 'default'}>
                {message.used_retrieval ? 'RAG' : 'Direct'}
              </Badge>
            )}
            {message.latency_ms !== undefined && (
              <span className="text-xs text-neutral-400">{message.latency_ms} ms</span>
            )}
          </div>
        )}

        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="w-full px-1">
            <SourcePanel sources={message.sources} />
          </div>
        )}
      </div>
    </div>
  )
}
