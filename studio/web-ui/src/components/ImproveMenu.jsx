import { useState } from 'react'
import { Sparkles, Loader2 } from 'lucide-react'
import { api } from '../services/api'
import DiffModal from './DiffModal'

/**
 * AI-assist control attached to an editable field.
 *
 * Props:
 *  - field: field family ('prose' | 'poem' | 'reflection' | ...) used to pick actions
 *  - text: current field value (string)
 *  - context: object passed to the backend (target_age, chapter_title, characters)
 *  - actions: the /api/actions catalogue
 *  - onAccept: (result) => void  — result is a string, or a string[] for list actions
 */
export default function ImproveMenu({ field, text, context, actions, onAccept }) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [proposal, setProposal] = useState(null)

  const choices = Object.entries(actions || {}).filter(([, a]) => a.field === field)
  if (choices.length === 0) return null

  const run = async (action) => {
    setOpen(false)
    setBusy(true)
    setError(null)
    try {
      const result = await api.improve(action, text || '', context || {})
      setProposal(result)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="relative inline-block">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        disabled={busy}
        title="Improve with AI"
        className="inline-flex items-center gap-1 rounded-md border border-primary-200 bg-primary-50 px-2 py-1 text-xs font-medium text-primary-700 hover:bg-primary-100 disabled:opacity-50"
      >
        {busy ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
        Improve
      </button>

      {open && (
        <div className="absolute right-0 z-20 mt-1 w-48 rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
          {choices.map(([name, a]) => (
            <button
              key={name}
              onClick={() => run(name)}
              className="block w-full px-3 py-1.5 text-left text-sm text-gray-700 hover:bg-gray-50"
            >
              {a.label}
            </button>
          ))}
        </div>
      )}

      {error && <p className="absolute right-0 mt-1 text-xs text-red-600">{String(error)}</p>}

      {proposal !== null && (
        <DiffModal
          original={text}
          proposed={proposal}
          onReject={() => setProposal(null)}
          onAccept={(result) => {
            setProposal(null)
            onAccept(result)
          }}
        />
      )}
    </div>
  )
}
