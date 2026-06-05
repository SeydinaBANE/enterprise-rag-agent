'use client'
import { useState } from 'react'
import { Link } from 'lucide-react'
import { toast } from 'sonner'
import { useIngestUrl } from '@/hooks/useDocuments'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'

export function UrlIngest() {
  const [url, setUrl] = useState('')
  const { mutateAsync, isPending } = useIngestUrl()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = url.trim()
    if (!trimmed) return
    try {
      const res = await mutateAsync({ url: trimmed })
      toast.success(`URL ingérée — ${res.chunks_stored} chunks stockés`)
      setUrl('')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Erreur lors de l\'ingestion de l\'URL')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Link className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-neutral-400" />
          <Input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://docs.example.com/page"
            disabled={isPending}
            className="pl-9"
            required
          />
        </div>
        <Button type="submit" disabled={!url.trim() || isPending} className="shrink-0">
          {isPending ? <Spinner size="sm" className="text-white" /> : 'Ingérer'}
        </Button>
      </div>
      <p className="text-xs text-neutral-400">
        Les adresses IP privées sont bloquées. Le domaine doit être accessible publiquement.
      </p>
    </form>
  )
}
