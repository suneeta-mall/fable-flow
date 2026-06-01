import { diffWords } from 'diff'

function asText(value) {
  return Array.isArray(value) ? value.join('\n') : (value ?? '')
}

export default function DiffModal({ original, proposed, onAccept, onReject }) {
  const parts = diffWords(asText(original), asText(proposed))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="flex max-h-[80vh] w-full max-w-3xl flex-col rounded-xl bg-white shadow-xl">
        <header className="border-b border-gray-100 px-5 py-3 text-sm font-semibold text-gray-700">
          Review AI suggestion
        </header>

        <div className="grid flex-1 grid-cols-1 gap-px overflow-auto bg-gray-100 md:grid-cols-2">
          <div className="bg-white p-4">
            <div className="mb-2 text-xs font-semibold uppercase text-gray-400">Proposed (diff)</div>
            <p className="whitespace-pre-wrap text-sm leading-relaxed">
              {parts.map((part, i) => (
                <span
                  key={i}
                  className={part.added ? 'diff-added' : part.removed ? 'diff-removed' : ''}
                >
                  {part.value}
                </span>
              ))}
            </p>
          </div>
          <div className="bg-white p-4">
            <div className="mb-2 text-xs font-semibold uppercase text-gray-400">Clean result</div>
            <p className="whitespace-pre-wrap text-sm leading-relaxed">{asText(proposed)}</p>
          </div>
        </div>

        <footer className="flex justify-end gap-2 border-t border-gray-100 px-5 py-3">
          <button
            onClick={onReject}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Reject
          </button>
          <button
            onClick={() => onAccept(proposed)}
            className="rounded-lg bg-primary-600 px-3 py-2 text-sm font-medium text-white hover:bg-primary-700"
          >
            Accept
          </button>
        </footer>
      </div>
    </div>
  )
}
