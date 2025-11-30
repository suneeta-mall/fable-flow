# Fable Flow Web UI

A modern web interface for managing story publishing with Fable Flow's AI-powered agents.

## ✨ NEW: Enhanced Interactive Editor!

The Story Editor has been significantly upgraded with powerful new features:

- 🤖 **AI Writing Assistant** - Get real-time feedback and suggestions with context-aware AI chat
- 📝 **Synopsis Editor** - Organize characters, plot points, themes, and learning objectives
- 📚 **Built-in Visual Guide** - Comprehensive help explaining how to use FableFlow
- 👁️ **Split View Mode** - Work with editor and AI chat side-by-side
- 🎨 **Improved UX** - Clean tab-based interface with color-coded panels

**See [ENHANCED_EDITOR.md](../ENHANCED_EDITOR.md) for full details and usage guide!**

## Features

- **Project Browser**: View all your story projects in an organized dashboard
- **Story Editor**: Edit story versions with Monaco Editor (VS Code-like experience)
  - **NEW**: AI chat for writing assistance
  - **NEW**: Synopsis editor for story planning
  - **NEW**: Built-in guide and help
  - **NEW**: Split view mode
- **Version Comparison**: Side-by-side diff view to compare story versions
- **Media Gallery**: Preview images, play audio/video, and download documents
- **Real-time Progress**: WebSocket updates for live processing status
- **Agent Controls**: Trigger publisher agents and restart processes after editing

## Tech Stack

- **Frontend**: React 18 + Vite
- **UI**: Tailwind CSS + Lucide Icons
- **Editor**: Monaco Editor
- **Diff**: React Diff Viewer
- **Backend**: FastAPI (Python)

## Prerequisites

- Node.js 18+ and npm/yarn
- Python 3.11+
- Fable Flow installed and configured

## Installation

### 1. Install Backend Dependencies

From the project root:

```bash
# Install FastAPI and related dependencies
pip install fastapi uvicorn[standard] websockets
```

Or add to your existing environment:

```bash
pip install -e ".[dev]"
```

### 2. Install Frontend Dependencies

```bash
cd web-ui
npm install
```

## Running the Application

### Start Backend Server

From the project root:

```bash
# Start the FastAPI backend on port 8000
python -m fable_flow.web_api
```

Or using uvicorn directly:

```bash
uvicorn fable_flow.web_api:app --reload --host 0.0.0.0 --port 8000
```

### Start Frontend Development Server

In a separate terminal, from the `web-ui` directory:

```bash
npm run dev
```

This will start the Vite dev server on http://localhost:3000

## Usage

1. Open your browser to http://localhost:3000
2. You'll see all projects from `docs/books/` directory
3. Click on a project to open it
4. Use the sidebar to navigate between:
   - **Edit Story**: Edit different story versions
   - **Compare Versions**: See differences between versions
   - **Media Gallery**: View generated images, audio, and videos

### Editing and Processing

1. Select a story version from the dropdown
2. Edit the content in the Monaco editor
3. Click **Save** to save changes
4. Click **Run Publisher** to process the story with AI agents
5. Watch real-time progress in the notification bell (top-right)

### Comparing Versions

1. Navigate to **Compare Versions**
2. Select two versions to compare
3. View side-by-side diff with highlighted changes

### Media Gallery

1. Navigate to **Media Gallery**
2. Switch between tabs: Images, Audio, Video, Documents
3. Click images for full-screen preview
4. Play audio/video directly in the browser
5. Download documents as needed

## Project Structure

```
web-ui/
├── src/
│   ├── components/      # Reusable UI components
│   │   ├── Header.jsx
│   │   └── Sidebar.jsx
│   ├── pages/          # Main application pages
│   │   ├── ProjectBrowser.jsx
│   │   ├── StoryEditor.jsx
│   │   ├── VersionCompare.jsx
│   │   └── MediaGallery.jsx
│   ├── services/       # API service layer
│   │   └── api.js
│   ├── hooks/          # Custom React hooks
│   │   └── useWebSocket.js
│   ├── styles/         # Global styles
│   │   └── index.css
│   ├── App.jsx         # Main app component
│   └── main.jsx        # Entry point
├── index.html
├── package.json
├── vite.config.js
└── tailwind.config.js
```

## API Endpoints

The backend provides the following REST API endpoints:

- `GET /api/projects` - List all projects
- `GET /api/projects/:series/:book` - Get project details
- `GET /api/story/:series/:book/:version` - Get story version content
- `POST /api/story/:series/:book/:version` - Update story version
- `GET /api/compare/:series/:book?v1=X&v2=Y` - Compare two versions
- `GET /api/media/:series/:book/:filename` - Serve media files
- `POST /api/process` - Start publishing process
- `WS /ws` - WebSocket for real-time updates

## Development

### Building for Production

```bash
npm run build
```

This creates an optimized production build in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Troubleshooting

### Backend not connecting

- Ensure FastAPI server is running on port 8000
- Check if `docs/books/` directory exists and contains projects

### Frontend build errors

- Delete `node_modules` and run `npm install` again
- Clear Vite cache: `rm -rf node_modules/.vite`

### WebSocket connection issues

- Check that both frontend and backend are running
- Verify CORS settings in `web_api.py`
- Check browser console for WebSocket errors

## License

MIT License - Same as Fable Flow main project
