import { Link } from 'react-router-dom'
import { BookOpen, Image, FileText, Play } from 'lucide-react'

function Sidebar({ projects, currentProject, onProjectSelect }) {
  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
      <div className="p-4 border-b border-gray-200 flex flex-col items-center">
        <img
          src="/logo.svg"
          alt="FableFlow"
          className="w-16 h-16 mb-2"
        />
        <h1 className="text-xl font-bold text-gray-800">FableFlow</h1>
        <p className="text-sm text-gray-500">Studio</p>
      </div>

      <nav className="flex-1 p-4 overflow-y-auto scrollbar-thin">
        <div className="mb-6">
          <Link
            to="/"
            className="flex items-center px-4 py-3 text-white bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 rounded-lg mb-4 shadow-md transition-all"
          >
            <BookOpen className="w-5 h-5 mr-3" />
            <div className="flex-1">
              <div className="font-semibold">Story Projects</div>
              <div className="text-xs text-indigo-100">Browse all projects</div>
            </div>
          </Link>
        </div>

        {currentProject && (
          <div>
            <h2 className="text-xs font-semibold text-gray-500 uppercase mb-2">Current Project</h2>
            <div className="bg-gray-50 rounded-lg p-3 mb-2">
              <p className="text-sm font-medium text-gray-800 mb-1">{currentProject.name}</p>
              <p className="text-xs text-gray-500 mb-3">{currentProject.versions.length} versions</p>

              <div className="space-y-1">
                <Link
                  to={`/project/${currentProject.path.split('/')[2]}/${currentProject.name}/edit`}
                  className="flex items-center px-2 py-1.5 text-sm text-gray-700 hover:bg-white rounded"
                >
                  <FileText className="w-3.5 h-3.5 mr-2" />
                  Edit Story
                </Link>
                <Link
                  to={`/project/${currentProject.path.split('/')[2]}/${currentProject.name}/compare`}
                  className="flex items-center px-2 py-1.5 text-sm text-gray-700 hover:bg-white rounded"
                >
                  <FileText className="w-3.5 h-3.5 mr-2" />
                  Compare Versions
                </Link>
                <Link
                  to={`/project/${currentProject.path.split('/')[2]}/${currentProject.name}/media`}
                  className="flex items-center px-2 py-1.5 text-sm text-gray-700 hover:bg-white rounded"
                >
                  <Image className="w-3.5 h-3.5 mr-2" />
                  Media Gallery
                </Link>
              </div>
            </div>
          </div>
        )}
      </nav>

      <div className="p-4 border-t border-gray-200 flex flex-col items-center">
        <div className="text-xs text-gray-500 text-center mb-2">
          <p>Version 0.1.0</p>
        </div>
        <img
          src="/powered_by_fabelflow.svg"
          alt="Powered by FableFlow"
          className="h-6 opacity-80"
        />
      </div>
    </div>
  )
}

export default Sidebar
