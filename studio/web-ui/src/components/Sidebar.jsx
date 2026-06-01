import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { BookOpen, Library } from 'lucide-react'
import { api } from '../services/api'

export default function Sidebar() {
  const [projects, setProjects] = useState([])
  const location = useLocation()
  const activeProject = new URLSearchParams(location.search).get('project')

  useEffect(() => {
    api.listProjects().then(setProjects).catch(() => setProjects([]))
  }, [])

  return (
    <aside className="flex w-64 flex-none flex-col border-r border-gray-200 bg-white">
      <Link to="/" className="flex items-center gap-2 border-b border-gray-100 px-5 py-4">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-600 text-white">
          <BookOpen size={18} />
        </span>
        <span className="font-semibold text-gray-800">FableFlow Studio</span>
      </Link>

      <div className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gray-400">
        <Library size={13} className="mr-1 inline" /> Projects
      </div>

      <nav className="scrollbar-thin flex-1 space-y-0.5 overflow-auto px-2 pb-4">
        {projects.length === 0 && (
          <p className="px-3 py-2 text-sm text-gray-400">No books found under the output root.</p>
        )}
        {projects.map((p) => (
          <Link
            key={p.id}
            to={`/edit?project=${encodeURIComponent(p.id)}`}
            className={
              'block truncate rounded-lg px-3 py-2 text-sm ' +
              (activeProject === p.id
                ? 'bg-primary-50 font-medium text-primary-700'
                : 'text-gray-700 hover:bg-gray-50')
            }
            title={p.title}
          >
            {p.title}
          </Link>
        ))}
      </nav>
    </aside>
  )
}
