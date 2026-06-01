import axios from 'axios'

// Relative base — Vite proxies /api to the FastAPI backend on :8000.
const API = '/api'

export const api = {
  listProjects: () => axios.get(`${API}/projects`).then((r) => r.data),

  getActions: () => axios.get(`${API}/actions`).then((r) => r.data),

  getBook: (project) =>
    axios.get(`${API}/book`, { params: { project } }).then((r) => r.data),

  saveBook: (project, book) =>
    axios.post(`${API}/book`, book, { params: { project } }).then((r) => r.data),

  mediaUrl: (project, path) =>
    `${API}/media?project=${encodeURIComponent(project)}&path=${encodeURIComponent(path)}`,

  improve: (action, text, context) =>
    axios.post(`${API}/ai/improve`, { action, text, context }).then((r) => r.data.result),

  chat: (project, message, history) =>
    axios.post(`${API}/ai/chat`, { project, message, history }).then((r) => r.data.response),

  publish: (project, formats) =>
    axios.post(`${API}/publish`, { formats }, { params: { project } }).then((r) => r.data),

  regenerateImage: (project, payload) =>
    axios.post(`${API}/image/regenerate`, payload, { params: { project } }).then((r) => r.data),

  acceptImage: (project, payload) =>
    axios.post(`${API}/image/accept`, payload, { params: { project } }).then((r) => r.data),

  discardImage: (project, payload) =>
    axios.post(`${API}/image/discard`, payload, { params: { project } }).then((r) => r.data),

  releaseImageModel: () => axios.post(`${API}/image/release`).then((r) => r.data),
}
