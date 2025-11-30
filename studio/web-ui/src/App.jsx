import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import Header from './components/Header'
import ProjectBrowser from './pages/ProjectBrowser'
import StoryEditor from './pages/StoryEditor'
import VersionCompare from './pages/VersionCompare'
import MediaGallery from './pages/MediaGallery'
import { useWebSocket } from './hooks/useWebSocket'

function App() {
  const [projects, setProjects] = useState([])
  const [currentProject, setCurrentProject] = useState(null)
  const { messages, sendMessage } = useWebSocket('ws://localhost:8000/ws')

  useEffect(() => {
    if (messages.length > 0) {
      const latestMessage = messages[messages.length - 1]
      console.log('WebSocket message:', latestMessage)
    }
  }, [messages])

  return (
    <Router>
      <div className="flex h-screen bg-gray-50">
        <Sidebar
          projects={projects}
          currentProject={currentProject}
          onProjectSelect={setCurrentProject}
        />

        <div className="flex-1 flex flex-col overflow-hidden">
          <Header currentProject={currentProject} wsMessages={messages} />

          <main className="flex-1 overflow-auto">
            <Routes>
              <Route
                path="/"
                element={
                  <ProjectBrowser
                    projects={projects}
                    setProjects={setProjects}
                    onProjectSelect={setCurrentProject}
                  />
                }
              />
              <Route
                path="/project/:series/:book/edit"
                element={<StoryEditor currentProject={currentProject} />}
              />
              <Route
                path="/project/:series/:book/compare"
                element={<VersionCompare currentProject={currentProject} />}
              />
              <Route
                path="/project/:series/:book/media"
                element={<MediaGallery currentProject={currentProject} />}
              />
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  )
}

export default App
