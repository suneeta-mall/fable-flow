import React, { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Image as ImageIcon, FileAudio, FileVideo, FileText, Download, Eye, Edit } from 'lucide-react'
import { api } from '../services/api'
import ImageEditor from '../components/ImageEditor'

function MediaGallery({ currentProject }) {
  const { series, book } = useParams()
  const [activeTab, setActiveTab] = useState('images')
  const [selectedMedia, setSelectedMedia] = useState(null)
  const [editingImage, setEditingImage] = useState(null)
  const [saving, setSaving] = useState(false)

  const tabs = [
    { id: 'images', label: 'Images', icon: ImageIcon },
    { id: 'audio', label: 'Audio', icon: FileAudio },
    { id: 'video', label: 'Video', icon: FileVideo },
    { id: 'documents', label: 'Documents', icon: FileText },
  ]

  const getMediaItems = () => {
    if (!currentProject) return []
    return currentProject.media[activeTab] || []
  }

  const getMediaUrl = (filename) => {
    return api.getMediaUrl(series, book, filename)
  }

  const handleMediaClick = (filename) => {
    setSelectedMedia(filename)
  }

  const handleEditImage = (filename) => {
    setEditingImage(filename)
  }

  const handleSaveImage = async (dataUrl, filename) => {
    try {
      setSaving(true)
      await api.saveMedia(series, book, dataUrl, filename)
      alert('Image saved successfully!')
      setEditingImage(null)
    } catch (error) {
      console.error('Error saving image:', error)
      alert('Failed to save image. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const handleCloseEditor = () => {
    setEditingImage(null)
  }

  const renderMediaPreview = (filename) => {
    const url = getMediaUrl(filename)

    if (activeTab === 'images') {
      return (
        <div
          key={filename}
          className="relative group bg-white rounded-lg overflow-hidden shadow hover:shadow-lg transition-shadow"
        >
          <img src={url} alt={filename} className="w-full h-48 object-cover" />
          <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-50 transition-opacity flex items-center justify-center gap-2">
            <button
              onClick={() => handleMediaClick(filename)}
              className="p-3 bg-blue-600 hover:bg-blue-700 rounded-lg text-white opacity-0 group-hover:opacity-100 transition-opacity"
              title="View"
            >
              <Eye className="w-5 h-5" />
            </button>
            <button
              onClick={() => handleEditImage(filename)}
              className="p-3 bg-green-600 hover:bg-green-700 rounded-lg text-white opacity-0 group-hover:opacity-100 transition-opacity"
              title="Edit"
            >
              <Edit className="w-5 h-5" />
            </button>
          </div>
          <div className="p-3">
            <p className="text-sm text-gray-700 truncate">{filename}</p>
          </div>
        </div>
      )
    }

    if (activeTab === 'audio') {
      return (
        <div
          key={filename}
          className="bg-white rounded-lg p-4 shadow hover:shadow-lg transition-shadow"
        >
          <div className="flex items-center mb-3">
            <FileAudio className="w-8 h-8 text-blue-500 mr-3" />
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-800">{filename}</p>
            </div>
          </div>
          <audio controls className="w-full" src={url}>
            Your browser does not support the audio element.
          </audio>
        </div>
      )
    }

    if (activeTab === 'video') {
      return (
        <div
          key={filename}
          className="bg-white rounded-lg overflow-hidden shadow hover:shadow-lg transition-shadow"
        >
          <video controls className="w-full" src={url}>
            Your browser does not support the video element.
          </video>
          <div className="p-3">
            <p className="text-sm text-gray-700 truncate">{filename}</p>
          </div>
        </div>
      )
    }

    if (activeTab === 'documents') {
      return (
        <div
          key={filename}
          className="bg-white rounded-lg p-4 shadow hover:shadow-lg transition-shadow"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <FileText className="w-8 h-8 text-green-500 mr-3" />
              <div>
                <p className="text-sm font-medium text-gray-800">{filename}</p>
              </div>
            </div>
            <a
              href={url}
              download
              className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg"
              title="Download"
            >
              <Download className="w-5 h-5" />
            </a>
          </div>
        </div>
      )
    }
  }

  const mediaItems = getMediaItems()

  return (
    <div className="h-full flex flex-col bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Media Gallery</h2>

        <div className="flex space-x-2">
          {tabs.map((tab) => {
            const Icon = tab.icon
            const count = currentProject?.media[tab.id]?.length || 0
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 rounded-lg flex items-center ${
                  activeTab === tab.id
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <Icon className="w-4 h-4 mr-2" />
                {tab.label}
                <span className="ml-2 text-sm">({count})</span>
              </button>
            )
          })}
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6">
        {mediaItems.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg border-2 border-dashed border-gray-300">
            {tabs.find((t) => t.id === activeTab) && (
              <>
                {React.createElement(tabs.find((t) => t.id === activeTab).icon, {
                  className: 'w-16 h-16 text-gray-400 mx-auto mb-4',
                })}
              </>
            )}
            <h3 className="text-lg font-semibold text-gray-700 mb-2">No {activeTab} found</h3>
            <p className="text-gray-500">This project doesn't have any {activeTab} yet</p>
          </div>
        ) : (
          <div
            className={
              activeTab === 'images'
                ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6'
                : 'space-y-4 max-w-3xl mx-auto'
            }
          >
            {mediaItems.map((filename) => renderMediaPreview(filename))}
          </div>
        )}
      </div>

      {selectedMedia && activeTab === 'images' && (
        <div
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50"
          onClick={() => setSelectedMedia(null)}
        >
          <div className="max-w-6xl max-h-screen p-4">
            <img
              src={getMediaUrl(selectedMedia)}
              alt={selectedMedia}
              className="max-w-full max-h-full object-contain"
            />
            <p className="text-white text-center mt-4">{selectedMedia}</p>
          </div>
        </div>
      )}

      {editingImage && (
        <ImageEditor
          imageUrl={getMediaUrl(editingImage)}
          imageName={editingImage}
          onSave={handleSaveImage}
          onClose={handleCloseEditor}
        />
      )}
    </div>
  )
}

export default MediaGallery
