import { useState } from 'react'
import Editor from '@monaco-editor/react'

/**
 * Escape-hatch raw JSON editor. Edits are parsed on "Apply"; invalid JSON is
 * reported inline and not pushed up. The backend re-validates against
 * BookContent on save, so this only guards against malformed JSON here.
 */
export default function RawJsonTab({ book, onApply }) {
  const [text, setText] = useState(() => JSON.stringify(book, null, 2))
  const [error, setError] = useState(null)

  const apply = () => {
    try {
      const parsed = JSON.parse(text)
      setError(null)
      onApply(parsed)
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-2">
        <span className="text-sm text-gray-500">
          Raw <code>book_content.json</code> — edits apply to the working copy; Save validates.
        </span>
        <button
          onClick={apply}
          className="rounded-lg bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700"
        >
          Apply to editor
        </button>
      </div>
      {error && <div className="bg-red-50 px-4 py-2 text-sm text-red-700">Invalid JSON: {error}</div>}
      <div className="flex-1">
        <Editor
          height="100%"
          defaultLanguage="json"
          value={text}
          onChange={(v) => setText(v ?? '')}
          options={{ minimap: { enabled: false }, fontSize: 13, wordWrap: 'on' }}
        />
      </div>
    </div>
  )
}
