import type { Upload } from '../useUploads'

interface Props {
  uploads: Upload[]
  onDismiss: (id: number) => void
}

const STATUS_TEXT: Record<Upload['status'], string> = {
  waiting: 'Waiting…',
  uploading: 'Uploading',
  reading: 'Reading…',
  done: 'Added',
  failed: 'Failed',
}

export function UploadList({ uploads, onDismiss }: Props) {
  if (uploads.length === 0) return null

  return (
    <ul className="uploads" aria-live="polite">
      {uploads.map((upload) => (
        <li key={upload.id} className={`upload-item upload-item--${upload.status}`}>
          <div className="upload-item__row">
            <span className="upload-item__name" title={upload.name}>
              {upload.name}
            </span>
            {upload.status === 'failed' && (
              <button
                type="button"
                className="upload-item__dismiss"
                onClick={() => onDismiss(upload.id)}
                aria-label={`Dismiss ${upload.name}`}
              >
                ×
              </button>
            )}
          </div>
          {upload.status !== 'failed' && (
            <div
              className="progress"
              role="progressbar"
              aria-label={`Uploading ${upload.name}`}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round(upload.progress * 100)}
            >
              <div className="progress__bar" style={{ width: `${upload.progress * 100}%` }} />
            </div>
          )}
          <span className="upload-item__status">
            {upload.status === 'uploading' ? `Uploading ${Math.round(upload.progress * 100)}%` : STATUS_TEXT[upload.status]}
            {upload.error && `: ${upload.error}`}
          </span>
        </li>
      ))}
    </ul>
  )
}
