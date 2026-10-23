import { useCallback, useRef, useState } from 'react'
import { addSampleDocuments, uploadDocument } from './api'

export interface Upload {
  id: number
  name: string
  /** 0 to 1: how much of the file has been sent. */
  progress: number
  status: 'waiting' | 'uploading' | 'reading' | 'done' | 'failed'
  error?: string
}

const MAX_BYTES = 10 * 1024 * 1024
const SUPPORTED = ['.pdf', '.txt', '.md']

/** Checks a file before sending it, so obvious mistakes fail instantly. */
function problemWith(file: File): string | null {
  const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
  if (!SUPPORTED.includes(extension)) return 'Only PDF, .txt and .md files are supported'
  if (file.size > MAX_BYTES) return 'Files must be at most 10 MB'
  if (file.size === 0) return 'The file is empty'
  return null
}

/**
 * The upload queue, shared by the sidebar and the empty-state drop zone.
 *
 * Files upload one at a time: the server embeds each file as it arrives, so
 * sending several at once would only make them all slower.
 */
export function useUploads(onDocumentsChanged: () => void) {
  const [uploads, setUploads] = useState<Upload[]>([])
  const [addingSamples, setAddingSamples] = useState(false)
  const [samplesError, setSamplesError] = useState<string | null>(null)
  const nextId = useRef(1)

  const uploadFiles = useCallback(
    async (files: File[]) => {
      const update = (id: number, change: Partial<Upload>) =>
        setUploads((all) => all.map((upload) => (upload.id === id ? { ...upload, ...change } : upload)))

      const jobs = files.map((file) => ({ file, id: nextId.current++ }))
      setUploads((all) => [
        ...all,
        ...jobs.map(({ file, id }) => ({ id, name: file.name, progress: 0, status: 'waiting' as const })),
      ])

      for (const { file, id } of jobs) {
        const problem = problemWith(file)
        if (problem) {
          update(id, { status: 'failed', error: problem })
          continue
        }
        update(id, { status: 'uploading' })
        try {
          const document = await uploadDocument(file, (fraction) =>
            update(id, fraction < 1 ? { progress: fraction } : { progress: 1, status: 'reading' }),
          )
          if (document.status === 'failed') update(id, { status: 'failed', error: document.error ?? 'Could not be read' })
          else update(id, { status: 'done' })
        } catch (err) {
          update(id, { status: 'failed', error: err instanceof Error ? err.message : 'Upload failed' })
        }
        onDocumentsChanged()
      }

      // Successful uploads now appear in the document list, so clear them from the queue
      // after a moment. Failures stay until dismissed, so their message can be read.
      window.setTimeout(() => setUploads((all) => all.filter((upload) => upload.status !== 'done')), 2000)
    },
    [onDocumentsChanged],
  )

  const dismiss = useCallback((id: number) => {
    setUploads((all) => all.filter((upload) => upload.id !== id))
  }, [])

  const addSamples = useCallback(async () => {
    setAddingSamples(true)
    setSamplesError(null)
    try {
      await addSampleDocuments()
      onDocumentsChanged()
    } catch (err) {
      setSamplesError(err instanceof Error ? err.message : "Couldn't add the sample documents")
    } finally {
      setAddingSamples(false)
    }
  }, [onDocumentsChanged])

  return { uploads, uploadFiles, dismiss, addSamples, addingSamples, samplesError }
}