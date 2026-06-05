export interface ChatRequest {
  message: string
  session_id?: string
}

export interface Source {
  document_id: string
  chunk: string
  score: number
}

export interface ChatResponse {
  answer: string
  sources: Source[]
  session_id: string
  used_retrieval: boolean
  latency_ms: number
}

export interface IngestResponse {
  document_id: string
  chunks_stored: number
  status: string
}

export interface IngestUrlRequest {
  url: string
}

export interface DocumentMeta {
  id: string
  chunks: number
  ingested_at: string
}

export interface DocumentsResponse {
  documents: DocumentMeta[]
  total: number
}

export interface HealthResponse {
  status: 'ok' | 'degraded'
  chromadb: 'ok' | 'error'
  llm: 'ok' | 'error'
  sessions: 'ok' | 'error'
  uptime_seconds: number
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  used_retrieval?: boolean
  latency_ms?: number
}
