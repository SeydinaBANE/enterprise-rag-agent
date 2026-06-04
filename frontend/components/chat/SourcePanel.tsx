'use client'
import { useState } from 'react'
import { ChevronDown, ChevronRight, FileText } from 'lucide-react'
import { cn, truncate } from '@/lib/utils'
import type { Source } from '@/types/api'

interface SourcePanelProps {
  sources: Source[]
}

export function SourcePanel({ sources }: SourcePanelProps) {
  const [open, setOpen] = useState(false)

  if (sources.length === 0) return null

  return (
    <div className="mt-2 rounded-md border border-neutral-100 bg-neutral-50">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-1.5 px-3 py-2 text-xs font-medium text-neutral-500 hover:text-neutral-700"
      >
        {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        {sources.length} source{sources.length > 1 ? 's' : ''}
      </button>

      {open && (
        <ul className={cn('divide-y divide-neutral-100 border-t border-neutral-100')}>
          {sources.map((s, i) => (
            <li key={i} className="px-3 py-2">
              <div className="flex items-center gap-1.5 text-xs font-medium text-neutral-600 mb-0.5">
                <FileText className="h-3 w-3 shrink-0" />
                <span className="truncate">{truncate(s.document_id, 40)}</span>
              </div>
              <p className="text-xs text-neutral-500 leading-relaxed">{s.chunk}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
