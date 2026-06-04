import { apiFetch } from './client'
import type { DocumentsResponse, IngestResponse, IngestUrlRequest } from '@/types/api'

export function listDocuments(): Promise<DocumentsResponse> {
  return apiFetch<DocumentsResponse>('/documents')
}

export function ingestFile(file: File): Promise<IngestResponse> {
  const form = new FormData()
  form.append('file', file)
  return apiFetch<IngestResponse>('/documents/ingest', {
    method: 'POST',
    body: form,
  })
}

export function ingestUrl(req: IngestUrlRequest): Promise<IngestResponse> {
  return apiFetch<IngestResponse>('/documents/ingest/url', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}
