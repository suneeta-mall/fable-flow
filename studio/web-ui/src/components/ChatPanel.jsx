import { useState } from 'react'
import { Send, Loader2, MessageSquare, X } from 'lucide-react'
import { api } from '../services/api'

export default function ChatPanel({ project }) {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)

  const send = async () => {
    const message = input.trim()
    if (!message || busy) return
    const history = messages
    setMessages([...history, { role: 'user', content: message }])
    setInput('')
    setBusy(true)
    try {
      const reply = await api.chat(project, message, history)
      setMessages((m) => [...m, { role: 'assistant', content: reply }])
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: `⚠️ ${e.response?.data?.detail || e.message}` },
      ])
    } finally {
      setBusy(false)
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-5 right-5 z-30 inline-flex items-center gap-2 rounded-full bg-primary-600 px-4 py-3 text-sm font-medium text-white shadow-lg hover:bg-primary-700"
      >
        <MessageSquare size={16} /> Ask the editor
      </button>
    )
  }

  return (
    <div className="fixed bottom-0 right-0 top-0 z-30 flex w-96 flex-col border-l border-gray-200 bg-white shadow-xl">
      <header className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
        <span className="text-sm font-semibold text-gray-700">AI editor chat</span>
        <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-gray-700">
          <X size={18} />
        </button>
      </header>

      <div className="scrollbar-thin flex-1 space-y-3 overflow-auto p-4">
        {messages.length === 0 && (
          <p className="text-sm text-gray-400">
            Ask for feedback, rewrites, title ideas, or anything about this book.
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={
              m.role === 'user'
                ? 'ml-auto max-w-[85%] rounded-lg bg-primary-600 px-3 py-2 text-sm text-white'
                : 'mr-auto max-w-[85%] whitespace-pre-wrap rounded-lg bg-gray-100 px-3 py-2 text-sm text-gray-800'
            }
          >
            {m.content}
          </div>
        ))}
        {busy && <Loader2 className="animate-spin text-gray-400" size={18} />}
      </div>

      <div className="flex gap-2 border-t border-gray-100 p-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder="Message…"
          className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
        />
        <button
          onClick={send}
          disabled={busy}
          className="rounded-lg bg-primary-600 px-3 py-2 text-white hover:bg-primary-700 disabled:opacity-50"
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  )
}
