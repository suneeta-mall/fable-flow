import axios from 'axios'

const API_BASE = 'http://localhost:8000/api'

export const api = {
  // Projects
  getProjects: async () => {
    const response = await axios.get(`${API_BASE}/projects`)
    return response.data
  },

  getProject: async (series, book) => {
    const response = await axios.get(`${API_BASE}/projects/${series}/${book}`)
    return response.data
  },

  createProject: async (series, book, initialStory = '', initialSynopsis = '') => {
    const response = await axios.post(`${API_BASE}/projects/create`, {
      series,
      book,
      initial_story: initialStory,
      initial_synopsis: initialSynopsis,
    })
    return response.data
  },

  // Stories
  getStoryVersion: async (series, book, version) => {
    const response = await axios.get(`${API_BASE}/story/${series}/${book}/${version}`)
    return response.data
  },

  updateStoryVersion: async (series, book, version, content) => {
    const response = await axios.post(`${API_BASE}/story/${series}/${book}/${version}`, {
      content,
      version,
    })
    return response.data
  },

  compareVersions: async (series, book, v1, v2) => {
    const response = await axios.get(`${API_BASE}/compare/${series}/${book}`, {
      params: { v1, v2 },
    })
    return response.data
  },

  // Media
  getMediaUrl: (series, book, filename) => {
    return `${API_BASE}/media/${series}/${book}/${filename}`
  },

  saveMedia: async (series, book, dataUrl, filename) => {
    const response = await axios.post(`${API_BASE}/media/${series}/${book}/save`, {
      data_url: dataUrl,
      filename: filename,
    })
    return response.data
  },

  // Processing
  processStory: async (projectPath, options = {}) => {
    const response = await axios.post(`${API_BASE}/process`, {
      project_path: projectPath,
      simple_publish: options.simplePublish ?? true,
      temperature: options.temperature ?? 0.9,
      seed: options.seed ?? 42,
    })
    return response.data
  },

  // AI Chat
  chatWithAI: async (message, context) => {
    const response = await axios.post(`${API_BASE}/chat`, {
      message,
      context,
    })
    return response.data
  },

  // Synopsis
  getSynopsis: async (series, book, file = 'draft_synopsis.txt') => {
    const response = await axios.get(`${API_BASE}/synopsis/${series}/${book}`, {
      params: { file }
    })
    return response.data
  },

  updateSynopsis: async (series, book, content, file = 'draft_synopsis.txt') => {
    const response = await axios.post(`${API_BASE}/synopsis/${series}/${book}`,
      { content },
      { params: { file } }
    )
    return response.data
  },

  // Formatted Book (Production Format)
  getFormattedBook: async (series, book) => {
    const response = await axios.get(`${API_BASE}/formatted/${series}/${book}`)
    return response.data
  },

  updateFormattedBook: async (series, book, content) => {
    const response = await axios.post(`${API_BASE}/formatted/${series}/${book}`, {
      content,
      version: 'formatted_book',
    })
    return response.data
  },
}
