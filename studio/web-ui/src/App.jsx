import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import ProjectBrowser from './pages/ProjectBrowser'
import BookEditor from './pages/BookEditor'

function App() {
  return (
    <Router>
      <div className="flex h-screen bg-gray-50 text-gray-900">
        <Sidebar />
        <main className="flex-1 overflow-hidden">
          <Routes>
            <Route path="/" element={<ProjectBrowser />} />
            <Route path="/edit" element={<BookEditor />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
