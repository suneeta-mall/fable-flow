import { useState } from 'react'
import { X, BookOpen, Folder, FileText, Sparkles } from 'lucide-react'

function NewProjectModal({ isOpen, onClose, onCreateProject }) {
  const [series, setSeries] = useState('')
  const [book, setBook] = useState('')
  const [initialStory, setInitialStory] = useState('')
  const [initialSynopsis, setInitialSynopsis] = useState('')
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)

    if (!series.trim() || !book.trim()) {
      setError('Series and book names are required')
      return
    }

    try {
      setCreating(true)
      await onCreateProject(series.trim(), book.trim(), initialStory, initialSynopsis)

      // Reset form
      setSeries('')
      setBook('')
      setInitialStory('')
      setInitialSynopsis('')
      onClose()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create project')
    } finally {
      setCreating(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center">
            <BookOpen className="w-6 h-6 text-indigo-600 mr-3" />
            <h2 className="text-2xl font-bold text-gray-800">Create New Project</h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          {/* Series and Book Name */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="flex items-center text-sm font-medium text-gray-700 mb-2">
                <Folder className="w-4 h-4 mr-2 text-indigo-600" />
                Series Name
              </label>
              <input
                type="text"
                value={series}
                onChange={(e) => setSeries(e.target.value)}
                placeholder="e.g., Adventures of Luna"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                required
              />
              <p className="text-xs text-gray-500 mt-1">The series or collection name</p>
            </div>

            <div>
              <label className="flex items-center text-sm font-medium text-gray-700 mb-2">
                <BookOpen className="w-4 h-4 mr-2 text-indigo-600" />
                Book Name
              </label>
              <input
                type="text"
                value={book}
                onChange={(e) => setBook(e.target.value)}
                placeholder="e.g., Luna's First Adventure"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                required
              />
              <p className="text-xs text-gray-500 mt-1">The specific book title</p>
            </div>
          </div>

          {/* Initial Story */}
          <div>
            <label className="flex items-center text-sm font-medium text-gray-700 mb-2">
              <FileText className="w-4 h-4 mr-2 text-green-600" />
              Initial Story Draft (Optional)
            </label>
            <textarea
              value={initialStory}
              onChange={(e) => setInitialStory(e.target.value)}
              placeholder="Start writing your story here, or leave blank to use the default template..."
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 font-mono text-sm resize-none"
              rows="8"
            />
            <p className="text-xs text-gray-500 mt-1">
              You can start writing immediately or use the editor after creating the project
            </p>
          </div>

          {/* Initial Synopsis */}
          <div>
            <label className="flex items-center text-sm font-medium text-gray-700 mb-2">
              <Sparkles className="w-4 h-4 mr-2 text-amber-600" />
              Initial Synopsis (Optional)
            </label>
            <textarea
              value={initialSynopsis}
              onChange={(e) => setInitialSynopsis(e.target.value)}
              placeholder="Add your story synopsis: overview, characters, plot points, themes, learning objectives..."
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 font-mono text-sm resize-none"
              rows="6"
            />
            <p className="text-xs text-gray-500 mt-1">
              Synopsis helps plan your story structure and maintain consistency
            </p>
          </div>

          {/* Info Box */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="text-sm font-semibold text-blue-900 mb-2">What happens next?</h4>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>✓ Project directory will be created at: docs/books/{series || '[series]'}/{book || '[book]'}</li>
              <li>✓ draft_story.txt will be initialized with your content or a template</li>
              <li>✓ draft_synopsis.txt will be created to help you plan your story</li>
              <li>✓ You'll be redirected to the editor to start writing</li>
            </ul>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end space-x-3 pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              disabled={creating}
              className="px-6 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={creating || !series.trim() || !book.trim()}
              className="px-6 py-2 bg-indigo-600 text-white hover:bg-indigo-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center transition-colors"
            >
              {creating ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Creating...
                </>
              ) : (
                <>
                  <BookOpen className="w-4 h-4 mr-2" />
                  Create Project
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default NewProjectModal
