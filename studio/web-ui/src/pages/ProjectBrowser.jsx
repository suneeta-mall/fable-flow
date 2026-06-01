import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { BookText, FileText, Film } from 'lucide-react'
import { api } from '../services/api'

function Badge({ ok, children }) {
  return (
    <span
      className={
        'rounded px-1.5 py-0.5 text-[11px] font-medium ' +
        (ok ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-400')
      }
    >
      {children}
    </span>
  )
}

export default function ProjectBrowser() {
  const [projects, setProjects] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    api.listProjects().then(setProjects).catch((e) => setError(e.message))
  }, [])

  return (
    <div className="scrollbar-thin h-full overflow-auto p-8">
      <h1 className="mb-1 text-2xl font-bold text-gray-800">Books</h1>
      <p className="mb-6 text-sm text-gray-500">
        Every <code>book_content.json</code> the producer wrote under the output root.
      </p>

      {error && <p className="text-red-600">Failed to load projects: {error}</p>}
      {!error && projects.length === 0 && (
        <p className="text-gray-500">
          No books found. Run <code>make run</code> to generate one, then refresh.
        </p>
      )}

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {projects.map((p) => (
          <Link
            key={p.id}
            to={`/edit?project=${encodeURIComponent(p.id)}`}
            className="group flex flex-col overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm transition hover:shadow-md"
          >
            <div className="flex h-40 items-center justify-center bg-gray-100">
              {p.cover ? (
                <img
                  src={api.mediaUrl(p.id, p.cover)}
                  alt={p.title}
                  className="h-full w-full object-cover"
                  onError={(e) => {
                    e.currentTarget.style.display = 'none'
                  }}
                />
              ) : (
                <BookText className="text-gray-300" size={40} />
              )}
            </div>
            <div className="flex flex-1 flex-col gap-2 p-4">
              <h2 className="font-semibold text-gray-800 group-hover:text-primary-700">{p.title}</h2>
              <p className="text-xs text-gray-500">
                {p.series ? `${p.series} · ` : ''}
                {p.genre || 'children’s book'}
              </p>
              <div className="mt-auto flex items-center gap-2 pt-2 text-gray-500">
                <span className="text-xs">{p.n_chapters} ch</span>
                <span className="text-xs">· age {p.target_age}</span>
                <span className="ml-auto flex gap-1">
                  <Badge ok={p.has_pdf}>
                    <FileText size={11} className="mr-0.5 inline" />
                    PDF
                  </Badge>
                  <Badge ok={p.has_epub}>
                    <Film size={11} className="mr-0.5 inline" />
                    EPUB
                  </Badge>
                </span>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
