'use client'
import { useRef, useState, type DragEvent } from 'react'
import { Upload, FileText } from 'lucide-react'
import { toast } from 'sonner'
import { useIngestFile } from '@/hooks/useDocuments'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { cn } from '@/lib/utils'

const ACCEPTED_TYPES = ['.pdf', '.txt', '.md', '.rst']
const MAX_MB = 50

export function FileUpload() {
  const inputRef = useRef<HTMLInputElement>(null)
  const { mutateAsync, isPending } = useIngestFile()
  const [dragging, setDragging] = useState(false)

  const validate = (file: File): string | null => {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!ACCEPTED_TYPES.includes(ext)) {
      return `Format non supporté — utilisez : ${ACCEPTED_TYPES.join(', ')}`
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      return `Fichier trop volumineux — max ${MAX_MB} MB`
    }
    return null
  }

  const upload = async (file: File) => {
    const error = validate(file)
    if (error) {
      toast.error(error)
      return
    }
    try {
      const res = await mutateAsync(file)
      toast.success(`Document ingéré — ${res.chunks_stored} chunks stockés`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Erreur lors de l\'ingestion')
    }
  }

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) upload(file)
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) upload(file)
    e.target.value = ''
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={cn(
        'flex flex-col items-center gap-3 rounded-xl border-2 border-dashed p-8 text-center transition-colors',
        dragging ? 'border-neutral-400 bg-neutral-50' : 'border-neutral-200 bg-white',
        isPending && 'pointer-events-none opacity-60',
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_TYPES.join(',')}
        onChange={handleChange}
        className="hidden"
      />

      {isPending ? (
        <Spinner size="lg" />
      ) : (
        <div className="rounded-full bg-neutral-100 p-3">
          {dragging ? (
            <FileText className="h-6 w-6 text-neutral-500" />
          ) : (
            <Upload className="h-6 w-6 text-neutral-400" />
          )}
        </div>
      )}

      <div>
        <p className="text-sm font-medium text-neutral-700">
          {isPending ? 'Ingestion en cours…' : 'Glissez un fichier ici'}
        </p>
        <p className="mt-0.5 text-xs text-neutral-400">
          {ACCEPTED_TYPES.join(', ')} · max {MAX_MB} MB
        </p>
      </div>

      {!isPending && (
        <Button variant="outline" size="sm" onClick={() => inputRef.current?.click()}>
          Parcourir
        </Button>
      )}
    </div>
  )
}
