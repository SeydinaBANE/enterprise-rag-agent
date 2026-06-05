'use client'
import { FileText, Inbox } from 'lucide-react'
import { useDocuments } from '@/hooks/useDocuments'
import { Spinner } from '@/components/ui/spinner'
import { formatRelativeDate, truncate } from '@/lib/utils'

export function DocumentTable() {
  const { data, isLoading, isError } = useDocuments()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner />
      </div>
    )
  }

  if (isError) {
    return (
      <p className="py-8 text-center text-sm text-red-500">
        Impossible de charger les documents — vérifiez la connexion au backend.
      </p>
    )
  }

  if (!data || data.documents.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 py-12 text-neutral-400">
        <Inbox className="h-8 w-8" />
        <p className="text-sm">Aucun document ingéré</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-neutral-100">
            <th className="py-2 pr-4 text-left font-medium text-neutral-500">Document ID</th>
            <th className="py-2 pr-4 text-right font-medium text-neutral-500">Chunks</th>
            <th className="py-2 text-right font-medium text-neutral-500">Ingéré</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-50">
          {data.documents.map((doc) => (
            <tr key={doc.id} className="hover:bg-neutral-50 transition-colors">
              <td className="py-2.5 pr-4">
                <div className="flex items-center gap-2">
                  <FileText className="h-3.5 w-3.5 shrink-0 text-neutral-400" />
                  <span className="font-mono text-xs text-neutral-600">{truncate(doc.id, 36)}</span>
                </div>
              </td>
              <td className="py-2.5 pr-4 text-right text-neutral-700">{doc.chunks}</td>
              <td className="py-2.5 text-right text-neutral-500">
                {formatRelativeDate(doc.ingested_at)}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t border-neutral-100">
            <td colSpan={3} className="py-2 text-right text-xs text-neutral-400">
              {data.total} document{data.total > 1 ? 's' : ''} au total
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  )
}
