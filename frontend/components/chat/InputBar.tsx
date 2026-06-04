'use client'
import { useRef, useState, type KeyboardEvent } from 'react'
import { Send, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const MAX_CHARS = 4096

interface InputBarProps {
  onSend: (message: string) => void
  onNewSession: () => void
  isLoading: boolean
}

export function InputBar({ onSend, onNewSession, isLoading }: InputBarProps) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSend = () => {
    const trimmed = value.trim()
    if (!trimmed || isLoading) return
    onSend(trimmed)
    setValue('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = () => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }

  const remaining = MAX_CHARS - value.length
  const overLimit = remaining < 0

  return (
    <div className="border-t border-neutral-200 bg-white px-4 py-3">
      <div className="flex items-end gap-2">
        <div className="relative flex-1">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value.slice(0, MAX_CHARS + 50))}
            onInput={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="Posez votre question… (Entrée pour envoyer, Maj+Entrée pour sauter une ligne)"
            disabled={isLoading}
            rows={1}
            className={cn(
              'w-full resize-none rounded-xl border bg-neutral-50 px-4 py-2.5 text-sm leading-relaxed placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-400 disabled:opacity-50',
              overLimit ? 'border-red-300' : 'border-neutral-200',
            )}
          />
          <span
            className={cn(
              'absolute bottom-2 right-3 text-xs',
              overLimit ? 'text-red-500' : remaining < 200 ? 'text-yellow-500' : 'text-neutral-300',
            )}
          >
            {remaining < 500 ? remaining : ''}
          </span>
        </div>

        <Button
          onClick={handleSend}
          disabled={!value.trim() || isLoading || overLimit}
          size="icon"
          className="mb-0.5 shrink-0"
          aria-label="Envoyer"
        >
          <Send className="h-4 w-4" />
        </Button>

        <Button
          variant="outline"
          size="icon"
          onClick={onNewSession}
          disabled={isLoading}
          className="mb-0.5 shrink-0"
          aria-label="Nouvelle session"
          title="Nouvelle session"
        >
          <RotateCcw className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
