'use client'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ingestFile, ingestUrl, listDocuments } from '@/lib/api/documents'
import type { IngestResponse, IngestUrlRequest } from '@/types/api'

const DOCUMENTS_KEY = ['documents'] as const

export function useDocuments() {
  return useQuery({
    queryKey: DOCUMENTS_KEY,
    queryFn: listDocuments,
    staleTime: 30_000,
  })
}

export function useIngestFile() {
  const qc = useQueryClient()
  return useMutation<IngestResponse, Error, File>({
    mutationFn: ingestFile,
    onSuccess: () => qc.invalidateQueries({ queryKey: DOCUMENTS_KEY }),
  })
}

export function useIngestUrl() {
  const qc = useQueryClient()
  return useMutation<IngestResponse, Error, IngestUrlRequest>({
    mutationFn: ingestUrl,
    onSuccess: () => qc.invalidateQueries({ queryKey: DOCUMENTS_KEY }),
  })
}
