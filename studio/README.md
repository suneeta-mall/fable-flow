# FableFlow Studio

A web-based workspace for managing multimedia story projects with FableFlow's AI-powered production pipeline.

## Table of Contents

- [What is This?](#what-is-this)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Features](#features)
- [Architecture](#architecture)
- [Usage Guide](#usage-guide)
- [API Reference](#api-reference)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Production Deployment](#production-deployment)
- [Support](#support)

## What is This?

FableFlow Studio is a web application that provides an interface for:

- Browse and manage story projects
- Edit story versions with Monaco editor (VS Code-like)
- Compare different versions side-by-side with diff highlighting
- Preview generated media (images, audio, video)
- Trigger AI production pipeline with one click
- Monitor real-time processing progress via WebSocket

**Important**: Studio is independent from the core FableFlow production pipeline in `producer/fable_flow/`. You can use the CLI without Studio.

### Why Separate?

Studio is kept separate from `producer/fable_flow/` because:

1. **Different Purpose**: Production pipeline vs. project management interface
2. **Optional**: You can use FableFlow CLI without Studio
3. **Different Dependencies**: Web frameworks not needed for core functionality
4. **Easier Maintenance**: Changes to Studio don't affect production code

## Quick Start

```bash
# Install dependencies
make studio-install

# Start Studio
make studio-start

# Stop Studio
make studio-stop
```

Then open **http://localhost:3000** in your browser.

### URLs

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (Swagger UI)

## Installation

### Prerequisites

- **Python 3.11+** - For API backend
- **Node.js 18+** - For frontend
- **Fable Flow core** - Must be installed

Check versions:

```bash
python3 --version  # Need 3.11+
node --version     # Need 18+
npm --version
```

### Quick Install

```bash
# Install Python dependencies
pip install fastapi uvicorn[standard] websockets aiofiles

# Install Node.js dependencies
cd studio/web-ui
npm install
cd ../..
```

### Manual Setup

**Step 1: Backend**

```bash
# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn[standard] websockets

# Verify
python3 -c "import fastapi; print('FastAPI OK')"
```

**Step 2: Frontend**

```bash
cd studio/web-ui
npm install
npm list react vite
```

**Step 3: Start Services**

Terminal 1 - Backend:
```bash
python3 studio/api.py
```

Terminal 2 - Frontend:
```bash
cd studio/web-ui
npm run dev
```

### Project Structure Setup

Studio expects stories organized as:

```
docs/books/{series}/{book}/
├── draft_story.txt
├── draft_synopsis.txt
├── final_story.txt
├── *.png (images)
├── *.mp3, *.m4a (audio)
├── *.mp4 (video)
└── *.pdf, *.epub (documents)
```

**Example: Create a new project**

```bash
mkdir -p docs/books/my_series/adventure_story

cat > docs/books/my_series/adventure_story/draft_story.txt << 'EOF'
Once upon a time, in a land far away, there lived a young adventurer
named Alex who dreamed of exploring the world...
EOF

cat > docs/books/my_series/adventure_story/draft_synopsis.txt << 'EOF'
A thrilling adventure story about Alex, a young explorer who discovers
a mysterious map leading to a hidden treasure.
EOF
```

Refresh browser - your new project appears!

## Features

### 1. Visual Project Browser

Dashboard view of all story projects with:
- Grid layout of project cards
- Metadata (version count, media files)
- Status badges (Draft, Final)
- Click-to-open navigation

### 2. Monaco Story Editor

VS Code-like editing experience:
- Syntax highlighting for Markdown
- Version selector dropdown
- Auto-save change indicators
- "Save" and "Discard" buttons
- "Run Publisher" to trigger AI agents
- Real-time syntax highlighting

### 3. Version Comparison

Side-by-side diff viewer:
- Select any two versions
- Color-coded changes (green=added, red=removed)
- Line-by-line differences
- Unified diff format

### 4. Media Gallery

Browse and preview generated content:
- **Images**: Grid view with lightbox preview
- **Audio**: In-browser playback controls
- **Video**: Embedded video player
- **Documents**: PDF/EPUB download links
- Tabbed interface by media type

### 5. Real-time Progress

WebSocket-powered live updates:
- Notification bell with event history
- Process status (started, completed, error)
- Project context in notifications
- Auto-dismiss old notifications

### 6. Agent Controls

One-click publishing workflow:
- Trigger publisher from UI
- Restart after editing files
- Monitor processing status
- View generated outputs

## Architecture

### Directory Structure

```
fable-flow/
├── producer/fable_flow/     # Production pipeline
│   ├── agents.py
│   ├── publisher.py
│   └── ...
│
└── studio/                  # Studio application (separate)
    ├── api.py               # FastAPI backend
    ├── web-ui/              # React frontend
    │   ├── src/
    │   │   ├── components/  # Header, Sidebar
    │   │   ├── pages/       # Browser, Editor, Compare, Gallery
    │   │   ├── services/    # API client
    │   │   └── hooks/       # WebSocket hook
    │   └── package.json
    └── README.md            # This file
```

### Communication Flow

```
┌─────────────────────────────────────────────┐
│          FableFlow Studio                   │
│                                             │
│  ┌──────────────┐    ┌──────────────┐     │
│  │   React UI   │───▶│   FastAPI    │     │
│  │  (port 3000) │◀───│  (port 8000) │     │
│  └──────────────┘    └──────┬───────┘     │
│                              │              │
└──────────────────────────────┼──────────────┘
                               │
            ┌──────────────────┼──────────────┐
            │      File I/O    │   API Calls  │
            ▼                  ▼              ▼
   ┌──────────────┐  ┌──────────────┐  ┌────────┐
   │ docs/books/  │  │ src/fable_   │  │ Config │
   │  - *.txt     │  │   flow/      │  │ .env   │
   │  - *.png     │  │   publisher  │  │        │
   └──────────────┘  └──────────────┘  └────────┘
```

### Technology Stack

**Backend**
- FastAPI 0.104+ - Modern async web framework
- Uvicorn - ASGI server with WebSocket
- Pydantic - Data validation

**Frontend**
- React 18.2 - UI framework
- Vite 5.0 - Build tool with HMR
- Tailwind CSS 3.3 - Utility-first styling
- Monaco Editor 4.6 - VS Code editor component
- React Router 6.20 - Client-side routing
- Axios 1.6 - HTTP client

### Integration with Production

Studio integrates cleanly:

```python
# studio/api.py imports from production (read-only)
from fable_flow.config import config
from fable_flow.publisher import main as publisher_main

# Calls production code without reimplementing
async def run_publisher():
    await publisher_main(story_fn=Path(project_path), ...)
```

## Usage Guide

### Creating a New Book

1. Create directory: `docs/books/{series}/{book}/`
2. Add `draft_story.txt` and `draft_synopsis.txt`
3. Refresh browser
4. Click project card to open
5. Edit in Story Editor
6. Click "Run Publisher"
7. Watch real-time notifications
8. View generated content in Media Gallery

### Editing an Existing Story

1. Open project from dashboard
2. Click "Edit Story" in sidebar
3. Select version (draft, final, etc.)
4. Make changes in Monaco Editor
5. Click "Save"
6. Optionally "Run Publisher" to regenerate
7. Compare versions to see changes

### Comparing Versions

1. Open project
2. Navigate to "Compare Versions"
3. Select version 1 (e.g., draft_story)
4. Select version 2 (e.g., final_story)
5. Review color-coded differences
6. Use insights to refine content

### Viewing Generated Media

1. Open project
2. Click "Media Gallery" in sidebar
3. Switch tabs: Images, Audio, Video, Documents
4. Click images for full-screen view
5. Play audio/video directly in browser
6. Download PDFs/EPUBs

## API Reference

### REST Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | API info |
| GET | `/health` | Health check |
| GET | `/api/projects` | List all projects |
| GET | `/api/projects/:series/:book` | Get project details |
| GET | `/api/story/:series/:book/:version` | Get story content |
| POST | `/api/story/:series/:book/:version` | Save story content |
| GET | `/api/compare/:series/:book?v1=X&v2=Y` | Compare versions |
| GET | `/api/media/:series/:book/:filename` | Serve media file |
| POST | `/api/process` | Start publishing |

### WebSocket

| Protocol | Endpoint | Purpose |
|----------|----------|---------|
| WS | `/ws` | Real-time updates |

**WebSocket Events:**
- `process_started` - Publishing begins
- `process_completed` - Publishing finished
- `process_error` - Error occurred
- `story_updated` - Story saved

## Development

### Modifying the Backend

Edit `studio/api.py`:

```python
@app.get("/api/new-endpoint")
async def new_feature():
    # Add new functionality
    return {"status": "success"}
```

### Modifying the Frontend

Add component in `studio/web-ui/src/components/`:

```jsx
// NewFeature.jsx
export default function NewFeature() {
  return <div>New Feature</div>
}
```

Add route in `studio/web-ui/src/App.jsx`:

```jsx
<Route path="/new-feature" element={<NewFeature />} />
```

### Customizing Styles

Edit `studio/web-ui/tailwind.config.js`:

```javascript
theme: {
  extend: {
    colors: {
      primary: { 500: '#your-color' }
    }
  }
}
```

### Hot Reload

Both services support hot reload:
- **Backend**: Run with `--reload` flag
- **Frontend**: Vite HMR (automatic)

## Troubleshooting

### Common Issues

**"No projects found"**
- Ensure `docs/books/` directory exists
- Check directory structure: `docs/books/{series}/{book}/`
- Verify `.txt` files exist
- Refresh browser

**Port 8000 already in use**
```bash
lsof -ti:8000 | xargs kill -9
# Or change port in viewer/api.py
```

**Port 3000 already in use**
```bash
# Use different port
cd studio/web-ui
npm run dev -- --port 3001
```

**Backend won't start**
```bash
pip install fastapi uvicorn[standard] websockets
```

**Frontend won't start**
```bash
cd studio/web-ui
rm -rf node_modules package-lock.json
npm install
```

**WebSocket connection failed**
- Verify both services are running
- Check firewall settings
- Try different browser
- Check browser console for errors

**Images not loading**
- Verify files exist in project directory
- Check file extensions (case-sensitive)
- Ensure backend has read permissions
- Check browser Network tab for 404s

### Debugging

**Backend logs:**
```bash
# Check logs
tail -f /tmp/fableflow-studio-backend.log

# Run with debug
python3 studio/api.py --log-level debug
```

**Frontend console:**
- Open DevTools (F12)
- Check Console tab for errors
- Check Network tab for API calls
- Verify WebSocket connection

### Verifying Installation

```bash
# Check backend health
curl http://localhost:8000/health

# Expected: {"status":"healthy","service":"fable-flow-api"}

# Check API docs
open http://localhost:8000/docs  # macOS
xdg-open http://localhost:8000/docs  # Linux
```

## Production Deployment

### Backend Deployment

```bash
# Install production server
pip install gunicorn

# Run with gunicorn
gunicorn studio.api:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Frontend Build

```bash
cd studio/web-ui
npm run build

# Serve with any static server
npm install -g serve
serve -s dist -p 3000
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name fableflow.example.com;

    # Frontend
    location / {
        root /path/to/studio/web-ui/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Security Considerations

**For Production:**
- Add authentication (JWT, OAuth)
- Restrict CORS origins
- Validate file paths (prevent directory traversal)
- Implement rate limiting
- Use HTTPS only
- Environment-based configuration
- Input sanitization

**Current (Development):**
- No authentication
- CORS enabled for localhost
- File system access unrestricted
- Suitable for local development only

### Environment Configuration

Create `.env` file:

```bash
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000
BOOKS_DIR=docs/books
MODEL_SERVER_URL=https://api.openai.com/v1
MODEL_API_KEY=your-api-key
DEFAULT_MODEL=gpt-4
```

## Support

### Documentation

- **web-ui/README.md** - Frontend documentation
- **web-ui/QUICK-START.md** - 2-minute quick reference
- **USER-GUIDE.md** - End-user guide

### Getting Help

- **Issues**: https://github.com/suneeta-mall/fable-flow/issues
- **Discussions**: https://github.com/suneeta-mall/fable-flow/discussions
- **Documentation**: https://suneeta-mall.github.io/fable-flow
- **Email**: suneetamall@gmail.com

### Contributing

Contributions welcome! To extend Studio:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### License

Apache License 2.0 - Same as FableFlow main project

---

**Ready to use!** Run `make studio-start` and open http://localhost:3000
