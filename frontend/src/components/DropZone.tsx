import { useRef, useState } from 'react'
import type { DragEvent } from 'react'

interface Props {
  onFiles: (files: File[]) => void
  /** "large" for the empty workspace, "compact" for the sidebar. */
  size?: 'large' | 'compact'
}

/**
 * An area you can drop files on, with a "browse" button for choosing them instead
 * (the keyboard-accessible route). Accepts several files at once.
 */
export function DropZone({ onFiles, size = 'compact' }: Props) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  // dragenter and dragleave also fire when the pointer moves over child elements,
  // so count them: the zone is only "left" when the count returns to zero.
  const depth = useRef(0)

  function handleDragEnter(event: DragEvent) {
    event.preventDefault()
    depth.current += 1
    setDragging(true)
  }

  function handleDragLeave() {
    depth.current -= 1
    if (depth.current === 0) setDragging(false)
  }

  function handleDrop(event: DragEvent) {
    event.preventDefault() // otherwise the browser opens the file instead
    depth.current = 0
    setDragging(false)
    const files = Array.from(event.dataTransfer.files)
    if (files.length > 0) onFiles(files)
  }

  return (
    <div
      className={`dropzone dropzone--${size} ${dragging ? 'dropzone--active' : ''}`}
      onDragEnter={handleDragEnter}
      onDragOver={(event) => event.preventDefault()}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <span className="dropzone__arrow" aria-hidden="true">
        ↑
      </span>
      {size === 'large' ? (
        <>
          <p className="dropzone__title">{dragging ? 'Drop to add' : 'Drop PDFs, .txt or .md files here'}</p>
          <p className="dropzone__hint">
            or{' '}
            <button type="button" className="link-button" onClick={() => inputRef.current?.click()}>
              browse your files
            </button>{' '}
            · up to 10 MB each
          </p>
        </>
      ) : (
        <p className="dropzone__hint">
          {dragging ? (
            'Drop to add'
          ) : (
            <>
              Drop files or{' '}
              <button type="button" className="link-button" onClick={() => inputRef.current?.click()}>
                browse
              </button>
            </>
          )}
        </p>
      )}
      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".pdf,.txt,.md"
        className="visually-hidden"
        tabIndex={-1}
        onChange={(event) => {
          const files = Array.from(event.target.files ?? [])
          event.target.value = '' // so choosing the same file again still triggers a change
          if (files.length > 0) onFiles(files)
        }}
      />
    </div>
  )
}
