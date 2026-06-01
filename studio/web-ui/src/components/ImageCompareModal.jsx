import { Loader2 } from 'lucide-react'
import { api } from '../services/api'

function Pane({ label, src, muted }) {
  return (
    <div className="flex flex-col">
      <div className="mb-2 text-xs font-semibold uppercase text-gray-400">{label}</div>
      <div className="flex aspect-square items-center justify-center overflow-hidden rounded-lg border border-gray-200 bg-gray-50">
        {src ? (
          <img src={src} alt={label} className="h-full w-full object-contain" />
        ) : (
          <span className="text-sm text-gray-400">{muted || 'none'}</span>
        )}
      </div>
    </div>
  )
}

/**
 * Side-by-side review of the live illustration vs. a freshly generated
 * candidate. Accept promotes the candidate to the target; Reject deletes it.
 */
export default function ImageCompareModal({
  project,
  currentPath,
  candidatePath,
  caption,
  busy,
  onAccept,
  onReject,
}) {
  const currentSrc = currentPath ? api.mediaUrl(project, currentPath) : null
  // candidate is freshly written; bust any cache.
  const candidateSrc = `${api.mediaUrl(project, candidatePath)}&t=${candidatePath.length}`

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="flex max-h-[88vh] w-full max-w-3xl flex-col rounded-xl bg-white shadow-xl">
        <header className="border-b border-gray-100 px-5 py-3 text-sm font-semibold text-gray-700">
          Review generated illustration
        </header>

        <div className="grid flex-1 grid-cols-2 gap-4 overflow-auto p-5">
          <Pane label="Current" src={currentSrc} muted="no image yet" />
          <Pane label="New (candidate)" src={candidateSrc} />
        </div>

        {caption && (
          <p className="px-5 pb-2 text-xs text-gray-500">
            <span className="font-medium">Prompt:</span> {caption}
          </p>
        )}

        <footer className="flex justify-end gap-2 border-t border-gray-100 px-5 py-3">
          <button
            onClick={onReject}
            disabled={busy}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            Reject
          </button>
          <button
            onClick={onAccept}
            disabled={busy}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary-600 px-3 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {busy && <Loader2 size={15} className="animate-spin" />}
            Accept
          </button>
        </footer>
      </div>
    </div>
  )
}
