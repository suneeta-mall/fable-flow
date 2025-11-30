"""FastAPI backend for Fable Flow Studio.

This is a separate service from the production pipeline in producer/fable_flow/.
It provides a web API for the Studio interface to manage and edit story projects.
"""

import asyncio
import base64
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Optional

import aiofiles
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from openai import AsyncOpenAI
from pydantic import BaseModel

# make sure to do make install to install fable_flow
from fable_flow.client import FableFlowChatClient
from fable_flow.config import config
from fable_flow.publisher import main as publisher_main


class ProjectInfo(BaseModel):
    """Project/Book information."""

    name: str
    path: str
    has_draft: bool = False
    has_final: bool = False
    versions: list[str] = []
    media: dict[str, list[str]] = {}


class StoryContent(BaseModel):
    """Story content for editing."""

    content: str
    version: str


class ProcessRequest(BaseModel):
    """Request to process a story."""

    project_path: str
    simple_publish: bool = True
    temperature: float = 0.9
    seed: int = 42


class ChatRequest(BaseModel):
    """Request for AI chat assistance."""

    message: str
    context: str = ""


class ChatResponse(BaseModel):
    """Response from AI chat."""

    response: str


class SynopsisRequest(BaseModel):
    """Request to update synopsis."""

    content: str


class CreateProjectRequest(BaseModel):
    """Request to create a new project."""

    series: str
    book: str
    initial_story: str = ""
    initial_synopsis: str = ""


class WebSocketManager:
    """Manage WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


# Initialize FastAPI app
app = FastAPI(
    title="Fable Flow Viewer API",
    description="Backend API for the Fable Flow Viewer - separate from production pipeline",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# WebSocket manager
ws_manager = WebSocketManager()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Fable Flow Viewer API",
        "version": "0.1.0",
        "note": "FableFlow's Editing portal for authors",
    }


@app.get("/api/projects", response_model=list[ProjectInfo])
async def list_projects():
    """List all projects in the docs/books directory."""
    books_dir = Path("docs/books")
    if not books_dir.exists():
        return []

    projects = []
    for series_dir in books_dir.iterdir():
        if series_dir.is_dir() and not series_dir.name.startswith("."):
            for book_dir in series_dir.iterdir():
                if book_dir.is_dir() and not book_dir.name.startswith("."):
                    project = await get_project_info(book_dir)
                    projects.append(project)

    return projects


@app.get("/api/projects/{series}/{book}", response_model=ProjectInfo)
async def get_project(series: str, book: str):
    """Get detailed information about a specific project."""
    book_dir = Path(f"docs/books/{series}/{book}")
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    return await get_project_info(book_dir)


@app.post("/api/projects/create")
async def create_project(request: CreateProjectRequest):
    """
    Create a new project with series/book structure.

    This will:
    1. Create the directory structure: docs/books/{series}/{book}
    2. Initialize draft_story.txt with initial content
    3. Initialize draft_synopsis.txt with initial content
    """
    try:
        # Validate series and book names (no special characters, spaces allowed)
        if not request.series or not request.book:
            raise HTTPException(status_code=400, detail="Series and book names are required")

        # Create sanitized names
        series_name = request.series.strip()
        book_name = request.book.strip()

        if not series_name or not book_name:
            raise HTTPException(status_code=400, detail="Series and book names cannot be empty")

        # Create project directory
        project_dir = Path(f"docs/books/{series_name}/{book_name}")

        # Check if project already exists
        if project_dir.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Project '{book_name}' already exists in series '{series_name}'",
            )

        # Create directory structure
        project_dir.mkdir(parents=True, exist_ok=True)

        # Create initial draft_story.txt
        draft_story_path = project_dir / "draft_story.txt"
        initial_story = (
            request.initial_story
            or f"""# {book_name}

## Chapter 1

Once upon a time...

[Start writing your story here]
"""
        )
        async with aiofiles.open(draft_story_path, "w") as f:
            await f.write(initial_story)

        # Create initial draft_synopsis.txt
        draft_synopsis_path = project_dir / "draft_synopsis.txt"
        initial_synopsis = (
            request.initial_synopsis
            or f"""# {book_name} - Story Synopsis

## Overview
[Brief overview of the story]

## Target Age Group
5-10 years old

## Characters
- Main Character: [Description]
- Supporting Characters: [Description]

## Plot Points
1. Beginning: [Setup]
2. Middle: [Conflict]
3. End: [Resolution]

## Themes
- [Theme 1]
- [Theme 2]

## Learning Objectives
- [Educational goal 1]
- [Educational goal 2]

## Tone & Style
[Description of tone and writing style]
"""
        )
        async with aiofiles.open(draft_synopsis_path, "w") as f:
            await f.write(initial_synopsis)

        # Broadcast success
        await ws_manager.broadcast(
            {
                "type": "project_created",
                "series": series_name,
                "book": book_name,
                "message": f"Project '{book_name}' created successfully",
            }
        )

        # Return project info
        project_info = await get_project_info(project_dir)
        return {
            "status": "success",
            "message": f"Project '{book_name}' created in series '{series_name}'",
            "project": project_info,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating project: {str(e)}") from e


async def get_project_info(book_dir: Path) -> ProjectInfo:
    """Extract project information from directory."""
    versions = []
    media = {"images": [], "audio": [], "video": [], "documents": []}

    # Check for story versions
    version_files = [
        "draft_story.txt",
        "CR_story.txt",
        "CM_story.txt",
        "ED_story.txt",
        "final_proof_story.txt",
        "final_story.txt",
    ]

    for version_file in version_files:
        if (book_dir / version_file).exists():
            versions.append(version_file.replace(".txt", ""))

    # Scan for media files
    if book_dir.exists():
        for file in book_dir.iterdir():
            if file.is_file():
                if file.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif"]:
                    media["images"].append(file.name)
                elif file.suffix.lower() in [".mp3", ".wav", ".m4a", ".ogg"]:
                    media["audio"].append(file.name)
                elif file.suffix.lower() in [".mp4", ".avi", ".mov"]:
                    media["video"].append(file.name)
                elif file.suffix.lower() in [".pdf", ".epub"]:
                    media["documents"].append(file.name)

    return ProjectInfo(
        name=book_dir.name,
        path=str(book_dir),
        has_draft=(book_dir / "draft_story.txt").exists(),
        has_final=(book_dir / "final_story.txt").exists(),
        versions=versions,
        media=media,
    )


@app.get("/api/story/{series}/{book}/{version}")
async def get_story_version(series: str, book: str, version: str):
    """Get a specific version of a story."""
    file_path = Path(f"docs/books/{series}/{book}/{version}.txt")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Story version '{version}' not found")

    async with aiofiles.open(file_path) as f:
        content = await f.read()

    return StoryContent(content=content, version=version)


@app.post("/api/story/{series}/{book}/{version}")
async def update_story_version(series: str, book: str, version: str, story: StoryContent):
    """Update a specific version of a story."""
    file_path = Path(f"docs/books/{series}/{book}/{version}.txt")
    file_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(file_path, "w") as f:
        await f.write(story.content)

    await ws_manager.broadcast(
        {
            "type": "story_updated",
            "series": series,
            "book": book,
            "version": version,
            "message": f"Story version '{version}' updated successfully",
        }
    )

    return {"status": "success", "message": f"Story version '{version}' saved"}


@app.get("/api/formatted/{series}/{book}")
async def get_formatted_book(series: str, book: str):
    """Get the formatted_book.html for production editing."""
    file_path = Path(f"docs/books/{series}/{book}/formatted_book.html")

    if not file_path.exists():
        # Return empty HTML template if file doesn't exist yet
        return StoryContent(
            content='<!DOCTYPE html>\n<html>\n<head>\n    <meta charset="UTF-8">\n    <title>Story Book</title>\n</head>\n<body>\n    <h1>Your Story</h1>\n    <p>Start editing your formatted book here...</p>\n</body>\n</html>',
            version="formatted_book",
        )

    async with aiofiles.open(file_path) as f:
        content = await f.read()

    return StoryContent(content=content, version="formatted_book")


@app.post("/api/formatted/{series}/{book}")
async def update_formatted_book(series: str, book: str, story: StoryContent):
    """Update the formatted_book.html."""
    file_path = Path(f"docs/books/{series}/{book}/formatted_book.html")
    file_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(file_path, "w") as f:
        await f.write(story.content)

    await ws_manager.broadcast(
        {
            "type": "formatted_book_updated",
            "series": series,
            "book": book,
            "message": "Formatted book updated successfully",
        }
    )

    return {"status": "success", "message": "Formatted book saved"}


@app.get("/api/media/{series}/{book}/{filename}")
async def get_media_file(series: str, book: str, filename: str):
    """Serve media files (images, audio, video)."""
    file_path = Path(f"docs/books/{series}/{book}/{filename}")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Media file not found")

    return FileResponse(file_path)


class MediaSaveRequest(BaseModel):
    """Request to save edited media."""

    data_url: str
    filename: str


class ImageEnhanceRequest(BaseModel):
    """Request to enhance image with AI."""

    data_url: str
    prompt: str
    previous_edits: list[str] = []  # For multi-turn editing


@app.post("/api/media/{series}/{book}/save")
async def save_media_file(series: str, book: str, request: MediaSaveRequest):
    """Save edited media file."""
    try:
        # Extract base64 data from data URL
        match = re.match(r"data:image/(\w+);base64,(.+)", request.data_url)
        if not match:
            raise HTTPException(status_code=400, detail="Invalid data URL format")

        image_format, base64_data = match.groups()

        # Decode base64 data
        image_data = base64.b64decode(base64_data)

        # Create backup of original if it exists
        file_path = Path(f"docs/books/{series}/{book}/{request.filename}")
        if file_path.exists():
            backup_path = file_path.with_suffix(f".backup{file_path.suffix}")
            shutil.copy2(file_path, backup_path)

        # Save the edited image
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(image_data)

        await ws_manager.broadcast(
            {
                "type": "media_updated",
                "series": series,
                "book": book,
                "filename": request.filename,
                "message": f"Media file '{request.filename}' updated successfully",
            }
        )

        return {"status": "success", "message": f"Media file saved: {request.filename}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving media: {str(e)}") from e


@app.post("/api/media/enhance")
async def enhance_image_with_ai(request: ImageEnhanceRequest):
    """
    Enhance image using OpenAI SDK with configurable base URL.

    Supports any OpenAI-compatible endpoint including:
    - Google Gemini API (via OpenAI-compatible endpoint)
    - OpenAI API
    - Self-hosted models (vLLM, Ollama, LocalAI, etc.)

    Configuration via environment variables:
    - IMAGE_API_BASE: Base URL for the API
      - Gemini: https://generativelanguage.googleapis.com/v1beta/openai/
      - OpenAI: https://api.openai.com/v1 (default)
      - Custom: https://your-api.com/v1
    - IMAGE_API_KEY: API key
    - IMAGE_MODEL: Model to use (default: gpt-4-vision-preview)
    """
    try:
        # Get configuration from environment
        api_base = os.getenv("IMAGE_API_BASE", "https://api.openai.com/v1")
        api_key = os.getenv("IMAGE_API_KEY")
        model = os.getenv("IMAGE_MODEL", "gpt-4-vision-preview")

        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="No API key found. Set IMAGE_API_KEY for IMAGE_API_BASE",
            )

        # Extract base64 data from data URL
        match = re.match(r"data:image/(\w+);base64,(.+)", request.data_url)
        if not match:
            raise HTTPException(status_code=400, detail="Invalid data URL format")

        image_format, base64_data = match.groups()

        # Build prompt with context from previous edits
        full_prompt = request.prompt
        if request.previous_edits:
            context = "Previous edits: " + ", ".join(request.previous_edits)
            full_prompt = f"{context}\n\nNew edit: {request.prompt}"

        # Initialize OpenAI client with custom base URL
        client = AsyncOpenAI(api_key=api_key, base_url=api_base)

        # Call chat completions API with vision
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/{image_format};base64,{base64_data}"},
                        },
                        {
                            "type": "text",
                            "text": f"Edit this image as follows: {full_prompt}. Return the edited image.",
                        },
                    ],
                }
            ],
            max_tokens=4096,
        )

        # Parse response
        if response.choices and len(response.choices) > 0:
            content = response.choices[0].message.content

            # Look for base64 image data in response
            if content:
                img_match = re.search(r"data:image/(\w+);base64,([A-Za-z0-9+/=]+)", content)
                if img_match:
                    enhanced_data_url = img_match.group(0)
                    return {
                        "status": "success",
                        "data_url": enhanced_data_url,
                        "message": "Image enhanced successfully",
                    }

        # If no image in response, return error
        raise HTTPException(
            status_code=500,
            detail="API did not return an enhanced image. Try a different prompt or check your model supports image generation.",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enhancing image: {str(e)}") from e


@app.post("/api/process")
async def process_story(request: ProcessRequest):
    """Start the publishing process for a story."""

    async def run_publisher():
        """Run publisher in background and broadcast updates."""
        try:
            await ws_manager.broadcast(
                {
                    "type": "process_started",
                    "project": request.project_path,
                    "message": "Publishing process started",
                }
            )

            # Run the publisher
            await publisher_main(
                story_fn=Path(request.project_path),
                output_dir=Path(request.project_path),
                simple_publish=request.simple_publish,
                temperature=request.temperature,
                seed=request.seed,
            )

            await ws_manager.broadcast(
                {
                    "type": "process_completed",
                    "project": request.project_path,
                    "message": "Publishing process completed successfully",
                }
            )

        except Exception as e:
            await ws_manager.broadcast(
                {
                    "type": "process_error",
                    "project": request.project_path,
                    "error": str(e),
                    "message": f"Publishing process failed: {str(e)}",
                }
            )

    # Start process in background
    asyncio.create_task(run_publisher())

    return {"status": "started", "message": "Publishing process initiated"}


@app.get("/api/compare/{series}/{book}")
async def compare_versions(series: str, book: str, v1: str, v2: str):
    """Compare two versions of a story."""
    path1 = Path(f"docs/books/{series}/{book}/{v1}.txt")
    path2 = Path(f"docs/books/{series}/{book}/{v2}.txt")

    if not path1.exists() or not path2.exists():
        raise HTTPException(status_code=404, detail="One or both versions not found")

    async with aiofiles.open(path1) as f:
        content1 = await f.read()

    async with aiofiles.open(path2) as f:
        content2 = await f.read()

    return {
        "version1": {"name": v1, "content": content1},
        "version2": {"name": v2, "content": content2},
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and receive messages
            _ = await websocket.receive_text()
            # Echo back or handle client messages if needed
            await websocket.send_json({"type": "pong", "message": "Connected"})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "fable-flow-api"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    """
    Chat with AI assistant for story feedback and suggestions.

    The AI will see the story context and provide helpful feedback.
    """
    try:
        # Initialize chat client using FableFlowChatClient
        from autogen_core import CancellationToken
        from autogen_core.models import SystemMessage, UserMessage

        client = FableFlowChatClient.create_chat_client(
            temperature=0.7,
        )

        # Construct prompt with context
        system_prompt = """You are a helpful assistant for children's book authors.

Answer the user's questions directly and simply. If they ask about their story, provide specific, actionable suggestions.

Keep your responses:
- Clear and concise
- Focused on the user's question
- Practical and actionable
- Age-appropriate for children aged 5-10"""

        user_prompt = request.message
        if request.context:
            user_prompt = f"Story excerpt:\n{request.context}\n\nQuestion: {request.message}"

        # Get AI response using the correct async API with proper message types
        response = await client.create(
            messages=[
                SystemMessage(content=system_prompt),
                UserMessage(content=user_prompt, source="user"),
            ],
            cancellation_token=CancellationToken(),
        )

        # Extract response text
        ai_response = response.content

        return ChatResponse(response=ai_response)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI chat error: {str(e)}") from e


@app.get("/api/synopsis/{series}/{book}")
async def get_synopsis(series: str, book: str, file: str = "draft_synopsis.txt"):
    """
    Get synopsis for a project.

    Args:
        series: Series name
        book: Book name
        file: Synopsis file to read (default: "draft_synopsis.txt", can be "synopsis.md")
    """
    try:
        # Validate file parameter
        allowed_files = ["draft_synopsis.txt", "synopsis.md"]
        if file not in allowed_files:
            raise HTTPException(
                status_code=400, detail=f"Invalid file parameter. Must be one of: {allowed_files}"
            )

        synopsis_file = Path(f"docs/books/{series}/{book}/{file}")
        if not synopsis_file.exists():
            # Return empty synopsis if file doesn't exist
            return {"content": "", "file": file}

        async with aiofiles.open(synopsis_file) as f:
            content = await f.read()

        return {"content": content, "file": file}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading synopsis: {str(e)}") from e


@app.post("/api/synopsis/{series}/{book}")
async def update_synopsis(
    series: str, book: str, request: SynopsisRequest, file: str = "draft_synopsis.txt"
):
    """
    Update synopsis for a project.

    Args:
        series: Series name
        book: Book name
        request: Synopsis content
        file: Synopsis file to write (default: "draft_synopsis.txt", can be "synopsis.md")
    """
    try:
        # Validate file parameter
        allowed_files = ["draft_synopsis.txt", "synopsis.md"]
        if file not in allowed_files:
            raise HTTPException(
                status_code=400, detail=f"Invalid file parameter. Must be one of: {allowed_files}"
            )

        synopsis_file = Path(f"docs/books/{series}/{book}/{file}")
        if not synopsis_file.parent.exists():
            raise HTTPException(status_code=404, detail="Project not found")

        # Write synopsis
        async with aiofiles.open(synopsis_file, "w") as f:
            await f.write(request.content)

        return {"status": "success", "message": f"{file} updated successfully", "file": file}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating synopsis: {str(e)}") from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
