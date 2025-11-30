import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BookOpen, Image, FileAudio, FileVideo, FileText, Play, Plus } from 'lucide-react'
import { api } from '../services/api'
import NewProjectModal from '../components/NewProjectModal'

function ProjectBrowser({ projects, setProjects, onProjectSelect }) {
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjects = async () => {
    try {
      setLoading(true)
      const data = await api.getProjects()
      setProjects(data)
    } catch (error) {
      console.error('Failed to load projects:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleProjectClick = (project) => {
    onProjectSelect(project)
    const pathParts = project.path.split('/')
    const series = pathParts[2]
    const book = pathParts[3]
    navigate(`/project/${series}/${book}/edit`)
  }

  const handleCreateProject = async (series, book, initialStory, initialSynopsis) => {
    try {
      const result = await api.createProject(series, book, initialStory, initialSynopsis)

      // Reload projects to include the new one
      await loadProjects()

      // Navigate to the new project
      navigate(`/project/${series}/${book}/edit`)

      // Optionally, select the new project
      if (result.project) {
        onProjectSelect(result.project)
      }
    } catch (error) {
      console.error('Failed to create project:', error)
      throw error
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading projects...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 mb-2">Story Projects</h1>
          <p className="text-gray-600">Browse versions, compare edits, and manage multimedia assets</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-indigo-600 text-white hover:bg-indigo-700 rounded-lg flex items-center transition-colors shadow-sm"
        >
          <Plus className="w-5 h-5 mr-2" />
          Create New Project
        </button>
      </div>

      {projects.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border-2 border-dashed border-gray-300">
          <BookOpen className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-700 mb-2">No Story Projects Yet</h3>
          <p className="text-gray-500 mb-4">
            Create your first project to start writing amazing children's books!
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center px-6 py-3 bg-indigo-600 text-white hover:bg-indigo-700 rounded-lg transition-colors shadow-sm"
          >
            <Plus className="w-5 h-5 mr-2" />
            Create Your First Project
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => (
            <div
              key={project.path}
              onClick={() => handleProjectClick(project)}
              className="bg-white rounded-lg border border-gray-200 hover:border-indigo-400 hover:shadow-lg transition-all cursor-pointer group"
            >
              <div className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-800 mb-1 group-hover:text-indigo-600 transition-colors">{project.name}</h3>
                    <p className="text-sm text-gray-500">{project.path.split('/')[2]}</p>
                  </div>
                  <BookOpen className="w-6 h-6 text-indigo-600 group-hover:text-purple-600 transition-colors" />
                </div>

                <div className="space-y-2 mb-4">
                  <div className="flex items-center text-sm text-gray-600">
                    <FileText className="w-4 h-4 mr-2" />
                    {project.versions.length} versions
                  </div>
                  <div className="flex items-center text-sm text-gray-600">
                    <Image className="w-4 h-4 mr-2" />
                    {project.media.images.length} images
                  </div>
                  <div className="flex items-center text-sm text-gray-600">
                    <FileAudio className="w-4 h-4 mr-2" />
                    {project.media.audio.length} audio files
                  </div>
                  {project.media.video.length > 0 && (
                    <div className="flex items-center text-sm text-gray-600">
                      <FileVideo className="w-4 h-4 mr-2" />
                      {project.media.video.length} videos
                    </div>
                  )}
                </div>

                <div className="flex gap-2 pt-3 border-t border-gray-100">
                  {project.has_draft && (
                    <span className="px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded">
                      Draft
                    </span>
                  )}
                  {project.has_final && (
                    <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded">
                      Final
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Project Modal */}
      <NewProjectModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreateProject={handleCreateProject}
      />
    </div>
  )
}

export default ProjectBrowser
