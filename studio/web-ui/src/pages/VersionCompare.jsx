import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { diffLines } from 'diff'
import { FileText, RefreshCw } from 'lucide-react'
import { api } from '../services/api'

function VersionCompare({ currentProject }) {
  const { series, book } = useParams()
  const [versions, setVersions] = useState([])
  const [version1, setVersion1] = useState('')
  const [version2, setVersion2] = useState('')
  const [comparison, setComparison] = useState(null)
  const [loading, setLoading] = useState(false)
  const [diffData, setDiffData] = useState([])

  useEffect(() => {
    if (currentProject && currentProject.versions.length > 0) {
      setVersions(currentProject.versions)
      if (currentProject.versions.length >= 2) {
        setVersion1(currentProject.versions[0])
        setVersion2(currentProject.versions[currentProject.versions.length - 1])
      }
    }
  }, [currentProject])

  useEffect(() => {
    if (version1 && version2) {
      loadComparison()
    }
  }, [version1, version2])

  const loadComparison = async () => {
    if (!version1 || !version2) return

    try {
      setLoading(true)
      const data = await api.compareVersions(series, book, version1, version2)
      setComparison(data)

      // Generate diff using diff library
      const diff = diffLines(data.version1.content, data.version2.content)
      setDiffData(diff)
    } catch (error) {
      console.error('Failed to load comparison:', error)
    } finally {
      setLoading(false)
    }
  }

  const renderDiff = () => {
    return (
      <div className="font-mono text-sm">
        {diffData.map((part, index) => {
          const bgColor = part.added
            ? 'bg-green-50'
            : part.removed
            ? 'bg-red-50'
            : 'bg-white'
          const textColor = part.added
            ? 'text-green-800'
            : part.removed
            ? 'text-red-800'
            : 'text-gray-800'
          const border = part.added
            ? 'border-l-4 border-green-500'
            : part.removed
            ? 'border-l-4 border-red-500'
            : 'border-l-4 border-gray-200'
          const prefix = part.added ? '+ ' : part.removed ? '- ' : '  '

          return (
            <div
              key={index}
              className={`${bgColor} ${textColor} ${border} px-4 py-1 whitespace-pre-wrap`}
            >
              {part.value.split('\n').map((line, lineIndex) => (
                <div key={lineIndex}>
                  {line && (
                    <>
                      <span className="text-gray-400 select-none">{prefix}</span>
                      {line}
                    </>
                  )}
                </div>
              ))}
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800">Compare Story Versions</h2>

          <div className="flex items-center space-x-4">
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">Version 1</label>
              <select
                value={version1}
                onChange={(e) => setVersion1(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {versions.map((version) => (
                  <option key={version} value={version}>
                    {version.replace(/_/g, ' ')}
                  </option>
                ))}
              </select>
            </div>

            <FileText className="w-5 h-5 text-gray-400 mt-6" />

            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">Version 2</label>
              <select
                value={version2}
                onChange={(e) => setVersion2(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {versions.map((version) => (
                  <option key={version} value={version}>
                    {version.replace(/_/g, ' ')}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={loadComparison}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center mt-6"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto bg-gray-50">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          </div>
        ) : comparison && diffData.length > 0 ? (
          <div className="bg-white m-4 rounded-lg shadow">
            <div className="grid grid-cols-2 gap-4 p-4 text-sm font-medium text-gray-700 border-b border-gray-200">
              <div className="text-center pb-2">
                <span className="inline-block px-3 py-1 bg-red-100 text-red-800 rounded">
                  {comparison.version1.name.replace(/_/g, ' ')}
                </span>
              </div>
              <div className="text-center pb-2">
                <span className="inline-block px-3 py-1 bg-green-100 text-green-800 rounded">
                  {comparison.version2.name.replace(/_/g, ' ')}
                </span>
              </div>
            </div>
            <div className="p-4">
              <div className="mb-3 text-sm text-gray-600">
                <span className="inline-flex items-center mr-4">
                  <span className="w-3 h-3 bg-green-200 border-l-4 border-green-500 mr-2"></span>
                  Added lines
                </span>
                <span className="inline-flex items-center mr-4">
                  <span className="w-3 h-3 bg-red-200 border-l-4 border-red-500 mr-2"></span>
                  Removed lines
                </span>
                <span className="inline-flex items-center">
                  <span className="w-3 h-3 bg-white border-l-4 border-gray-200 mr-2"></span>
                  Unchanged lines
                </span>
              </div>
              {renderDiff()}
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-gray-500">
              <FileText className="w-16 h-16 mx-auto mb-4 text-gray-400" />
              <p>Select versions to compare</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default VersionCompare
