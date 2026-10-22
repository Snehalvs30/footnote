// Shapes of the data the API returns. They mirror the Pydantic schemas in the backend.

export type DocumentStatus = 'processing' | 'ready' | 'failed'

export interface DocumentInfo {
  id: string
  filename: string
  status: DocumentStatus
  page_count: number | null
  chunk_count: number
  error: string | null
  created_at: string
}

/** One numbered passage an answer may cite, from the "sources" event. */
export interface Source {
  number: number
  document_id: string
  filename: string
  page_number: number
  chunk_index: number
  score: number
  excerpt: string
}

export interface User {
  id: string
  email: string
}