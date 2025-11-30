import { useState, useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import Editor from '@monaco-editor/react'
import {
  Save, Play, RotateCcw, FileText, AlertCircle, CheckCircle,
  MessageSquare, Send, Sparkles, BookOpen, HelpCircle,
  FileEdit, Eye, Lightbulb, Zap, Code
} from 'lucide-react'
import { api } from '../services/api'

function StoryEditor({ currentProject }) {
  const { series, book } = useParams()
  const [versions, setVersions] = useState([])
  const [selectedVersion, setSelectedVersion] = useState('')
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [message, setMessage] = useState(null)
  const [hasChanges, setHasChanges] = useState(false)

  // Panel states
  const [activePanel, setActivePanel] = useState('editor')
  const [splitView, setSplitView] = useState(false)

  // AI Chat states
  const [chatMessages, setChatMessages] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const chatMessagesEndRef = useRef(null)

  // Synopsis states
  const [synopsis, setSynopsis] = useState('')
  const [synopsisLoading, setSynopsisLoading] = useState(false)
  const [synopsisHasChanges, setSynopsisHasChanges] = useState(false)
  const [synopsisFile, setSynopsisFile] = useState('draft_synopsis.txt')

  // Formatted book states
  const [formattedContent, setFormattedContent] = useState('')
  const [formattedLoading, setFormattedLoading] = useState(false)
  const [formattedHasChanges, setFormattedHasChanges] = useState(false)

  // Inline AI chat states
  const [showInlineChat, setShowInlineChat] = useState(false)
  const [selectedText, setSelectedText] = useState('')
  const [inlineChatPosition, setInlineChatPosition] = useState({ x: 0, y: 0 })
  const editorRef = useRef(null)

  useEffect(() => {
    if (currentProject && currentProject.versions.length > 0) {
      setVersions(currentProject.versions)
      const defaultVersion = currentProject.versions.includes('final_story')
        ? 'final_story'
        : currentProject.versions.includes('draft_story')
        ? 'draft_story'
        : currentProject.versions[0]
      setSelectedVersion(defaultVersion)
    }
  }, [currentProject])

  useEffect(() => {
    if (selectedVersion) {
      loadStoryVersion()
    }
  }, [selectedVersion])

  useEffect(() => {
    if (series && book) {
      loadSynopsis()
      loadFormattedBook()
    }
  }, [series, book])

  useEffect(() => {
    scrollToBottomOfChat()
  }, [chatMessages])

  const scrollToBottomOfChat = () => {
    chatMessagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const loadStoryVersion = async () => {
    try {
      setLoading(true)
      const data = await api.getStoryVersion(series, book, selectedVersion)
      setContent(data.content)
      setHasChanges(false)
    } catch (error) {
      showMessage('error', 'Failed to load story version')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const loadSynopsis = async (file = synopsisFile) => {
    try {
      setSynopsisLoading(true)
      const data = await api.getSynopsis(series, book, file)
      setSynopsis(data.content || '')
      setSynopsisHasChanges(false)
    } catch (error) {
      console.log('Synopsis not found, creating new one')
      setSynopsis('# Story Synopsis\n\n## Overview\n\n## Characters\n\n## Plot Points\n\n## Themes\n\n## Learning Objectives\n')
    } finally {
      setSynopsisLoading(false)
    }
  }

  // Reload synopsis when file changes
  useEffect(() => {
    if (series && book && synopsisFile) {
      loadSynopsis(synopsisFile)
    }
  }, [synopsisFile])

  const handleSave = async () => {
    try {
      setSaving(true)
      await api.updateStoryVersion(series, book, selectedVersion, content)
      showMessage('success', 'Story saved successfully')
      setHasChanges(false)
    } catch (error) {
      showMessage('error', 'Failed to save story')
      console.error(error)
    } finally {
      setSaving(false)
    }
  }

  const handleSaveSynopsis = async () => {
    try {
      setSynopsisLoading(true)
      await api.updateSynopsis(series, book, synopsis, synopsisFile)
      showMessage('success', `${synopsisFile} saved successfully`)
      setSynopsisHasChanges(false)
    } catch (error) {
      showMessage('error', 'Failed to save synopsis')
      console.error(error)
    } finally {
      setSynopsisLoading(false)
    }
  }

  const loadFormattedBook = async () => {
    try {
      setFormattedLoading(true)
      const data = await api.getFormattedBook(series, book)
      setFormattedContent(data.content || '')
      setFormattedHasChanges(false)
    } catch (error) {
      console.log('Formatted book not found, using template')
      setFormattedContent('')
    } finally {
      setFormattedLoading(false)
    }
  }

  const handleSaveFormattedBook = async () => {
    try {
      setFormattedLoading(true)
      await api.updateFormattedBook(series, book, formattedContent)
      showMessage('success', 'Production format saved successfully')
      setFormattedHasChanges(false)
    } catch (error) {
      showMessage('error', 'Failed to save production format')
      console.error(error)
    } finally {
      setFormattedLoading(false)
    }
  }

  const handleFormattedContentChange = (value) => {
    setFormattedContent(value || '')
    setFormattedHasChanges(true)
  }

  const handleProcess = async () => {
    if (hasChanges) {
      await handleSave()
    }

    try {
      setProcessing(true)
      const projectPath = `docs/books/${series}/${book}`
      await api.processStory(projectPath, { simplePublish: true })
      showMessage('success', 'Processing started! Check notifications for progress.')
    } catch (error) {
      showMessage('error', 'Failed to start processing')
      console.error(error)
    } finally {
      setProcessing(false)
    }
  }

  const handleSendChat = async () => {
    if (!chatInput.trim()) return

    const userMessage = chatInput.trim()
    setChatInput('')

    // Add user message
    setChatMessages(prev => [...prev, { role: 'user', content: userMessage }])

    try {
      setChatLoading(true)
      // Get context from story (first 4000 characters)
      const context = content.substring(0, 4000)
      const response = await api.chatWithAI(userMessage, context)

      // Add AI response
      setChatMessages(prev => [...prev, { role: 'assistant', content: response.response }])
    } catch (error) {
      showMessage('error', 'Failed to get AI response')
      console.error(error)
      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.'
      }])
    } finally {
      setChatLoading(false)
    }
  }

  const handleQuickPrompt = (prompt) => {
    setChatInput(prompt)
  }

  // Inline AI Actions
  const handleEditorMount = (editor) => {
    editorRef.current = editor

    // Add context menu for AI actions
    editor.addAction({
      id: 'ai-improve',
      label: '✨ Improve with AI',
      contextMenuGroupId: 'ai-actions',
      contextMenuOrder: 1,
      run: async (ed) => {
        const selection = ed.getSelection()
        const selectedText = ed.getModel().getValueInRange(selection)
        if (selectedText) {
          await handleInlineAI(ed, selection, selectedText, 'Improve this text for a children\'s book. Return ONLY the improved text, no explanations.')
        }
      }
    })

    editor.addAction({
      id: 'ai-expand',
      label: '📝 Expand with AI',
      contextMenuGroupId: 'ai-actions',
      contextMenuOrder: 2,
      run: async (ed) => {
        const selection = ed.getSelection()
        const selectedText = ed.getModel().getValueInRange(selection)
        if (selectedText) {
          await handleInlineAI(ed, selection, selectedText, 'Expand this text with more details and descriptions. Return ONLY the expanded text, no explanations.')
        }
      }
    })

    editor.addAction({
      id: 'ai-simplify',
      label: '🎯 Simplify for children',
      contextMenuGroupId: 'ai-actions',
      contextMenuOrder: 3,
      run: async (ed) => {
        const selection = ed.getSelection()
        const selectedText = ed.getModel().getValueInRange(selection)
        if (selectedText) {
          await handleInlineAI(ed, selection, selectedText, 'Simplify this text for 5-10 year old children. Use simpler words and shorter sentences. Return ONLY the simplified text, no explanations.')
        }
      }
    })
  }

  const handleInlineAI = async (editor, selection, text, prompt) => {
    try {
      setChatLoading(true)
      showMessage('info', '✨ AI is working...')

      const fullPrompt = `${prompt}\n\nOriginal text:\n"${text}"\n\nImproved text:`
      const response = await api.chatWithAI(fullPrompt, '')

      // Replace the selected text with AI response
      const improvedText = response.response.trim()

      editor.executeEdits('ai-inline-edit', [
        {
          range: selection,
          text: improvedText,
          forceMoveMarkers: true
        }
      ])

      // Mark as changed
      setHasChanges(true)

      showMessage('success', '✨ Text improved by AI!')
    } catch (error) {
      showMessage('error', 'Failed to get AI suggestion')
      console.error(error)
    } finally {
      setChatLoading(false)
    }
  }

  const showMessage = (type, text) => {
    setMessage({ type, text })
    setTimeout(() => setMessage(null), 5000)
  }

  const handleContentChange = (value) => {
    setContent(value || '')
    setHasChanges(true)
  }

  const handleSynopsisChange = (e) => {
    setSynopsis(e.target.value)
    setSynopsisHasChanges(true)
  }

  const quickPrompts = [
    { icon: '💡', text: 'What should happen next?', prompt: 'What should happen next in this story?' },
    { icon: '👥', text: 'How can I develop this character?', prompt: 'How can I develop this character better?' },
    { icon: '💬', text: 'Improve the dialogue', prompt: 'How can I improve the dialogue?' },
    { icon: '📚', text: 'Add educational content', prompt: 'How can I add educational content?' },
    { icon: '🎯', text: 'Is this age-appropriate?', prompt: 'Is this age-appropriate for 5-10 year olds?' },
    { icon: '✨', text: 'Make it more engaging', prompt: 'How can I make this more engaging?' },
  ]

  const renderGuide = () => (
    <div className="p-6 overflow-y-auto h-full bg-gradient-to-b from-blue-50 to-white">
      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-8">
          <Sparkles className="w-16 h-16 text-blue-600 mx-auto mb-4" />
          <h2 className="text-3xl font-bold text-gray-900 mb-2">
            FableFlow Interactive Editor
          </h2>
          <p className="text-gray-600">
            Create amazing children's books with AI-powered assistance
          </p>
        </div>

        <div className="space-y-6">
          {/* What is FableFlow */}
          <div className="bg-white rounded-lg shadow-sm p-6 border border-blue-100">
            <h3 className="text-xl font-semibold text-blue-900 mb-3 flex items-center">
              <BookOpen className="w-5 h-5 mr-2" />
              What is FableFlow?
            </h3>
            <p className="text-gray-700 leading-relaxed">
              FableFlow is an AI-powered platform that transforms your story drafts into
              professionally illustrated, narrated, and formatted children's books. Our
              multi-agent system enhances your narrative, generates illustrations, creates
              audio narration, and produces multimedia content—all optimized for children's
              learning and engagement.
            </p>
          </div>

          {/* How to Use */}
          <div className="bg-white rounded-lg shadow-sm p-6 border border-green-100">
            <h3 className="text-xl font-semibold text-green-900 mb-4 flex items-center">
              <Zap className="w-5 h-5 mr-2" />
              How to Use This Editor
            </h3>
            <div className="space-y-4">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 w-8 h-8 bg-green-100 rounded-full flex items-center justify-center text-green-700 font-semibold">
                  1
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900">Edit Your Story</h4>
                  <p className="text-gray-600 text-sm">
                    Use the main editor to write and refine your story. The Monaco editor
                    provides syntax highlighting, auto-completion, and other IDE features.
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 w-8 h-8 bg-green-100 rounded-full flex items-center justify-center text-green-700 font-semibold">
                  2
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900">Get AI Assistance</h4>
                  <p className="text-gray-600 text-sm">
                    Switch to the AI Chat panel to ask questions about your story, get
                    suggestions, or request improvements. The AI sees your story content
                    and provides contextual feedback.
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 w-8 h-8 bg-green-100 rounded-full flex items-center justify-center text-green-700 font-semibold">
                  3
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900">Organize with Synopsis</h4>
                  <p className="text-gray-600 text-sm">
                    Use the Synopsis panel to keep track of characters, plot points, themes,
                    and learning objectives. This helps maintain consistency throughout your story.
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 w-8 h-8 bg-green-100 rounded-full flex items-center justify-center text-green-700 font-semibold">
                  4
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900">Save and Process</h4>
                  <p className="text-gray-600 text-sm">
                    Click Save to save your changes, then Run Publisher to process your
                    story with AI agents that generate illustrations, narration, and more.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Tips & Best Practices */}
          <div className="bg-white rounded-lg shadow-sm p-6 border border-purple-100">
            <h3 className="text-xl font-semibold text-purple-900 mb-4 flex items-center">
              <Lightbulb className="w-5 h-5 mr-2" />
              Tips & Best Practices
            </h3>
            <ul className="space-y-2 text-gray-700">
              <li className="flex items-start">
                <span className="text-purple-600 mr-2">✓</span>
                <span><strong>Be specific:</strong> When asking AI for help, provide specific context about what you want to improve</span>
              </li>
              <li className="flex items-start">
                <span className="text-purple-600 mr-2">✓</span>
                <span><strong>Save frequently:</strong> Use Ctrl+S or click Save to avoid losing your work</span>
              </li>
              <li className="flex items-start">
                <span className="text-purple-600 mr-2">✓</span>
                <span><strong>Update synopsis:</strong> Keep your synopsis current as your story evolves</span>
              </li>
              <li className="flex items-start">
                <span className="text-purple-600 mr-2">✓</span>
                <span><strong>Use quick prompts:</strong> Try the quick prompt buttons in AI Chat for common tasks</span>
              </li>
              <li className="flex items-start">
                <span className="text-purple-600 mr-2">✓</span>
                <span><strong>Split view:</strong> Enable split view to see AI chat alongside your editor</span>
              </li>
            </ul>
          </div>

          {/* Keyboard Shortcuts */}
          <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-200">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">
              ⌨️ Keyboard Shortcuts
            </h3>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div><kbd className="px-2 py-1 bg-gray-100 rounded">Ctrl+S</kbd> Save</div>
              <div><kbd className="px-2 py-1 bg-gray-100 rounded">Ctrl+Z</kbd> Undo</div>
              <div><kbd className="px-2 py-1 bg-gray-100 rounded">Ctrl+F</kbd> Find</div>
              <div><kbd className="px-2 py-1 bg-gray-100 rounded">Ctrl+H</kbd> Replace</div>
              <div><kbd className="px-2 py-1 bg-gray-100 rounded">Ctrl+Shift+F</kbd> Format</div>
              <div><kbd className="px-2 py-1 bg-gray-100 rounded">Alt+↑/↓</kbd> Move line</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )

  const renderAIChat = () => (
    <div className="h-full flex flex-col bg-gradient-to-b from-purple-50 to-white">
      {/* Guide Section */}
      <div className="bg-white border-b border-purple-200 p-4">
        <h3 className="text-lg font-semibold text-purple-900 mb-2 flex items-center">
          <MessageSquare className="w-5 h-5 mr-2" />
          AI Writing Assistant
        </h3>
        <p className="text-sm text-gray-600 mb-3">
          Ask questions about your story and get AI-powered suggestions for improvement.
        </p>
        <div className="flex flex-wrap gap-2">
          {quickPrompts.map((prompt, idx) => (
            <button
              key={idx}
              onClick={() => handleQuickPrompt(prompt.prompt)}
              className="px-3 py-1.5 text-xs bg-purple-100 hover:bg-purple-200 text-purple-700 rounded-full transition-colors flex items-center"
              title={prompt.text}
            >
              <span className="mr-1">{prompt.icon}</span>
              <span className="hidden sm:inline">{prompt.text.split(' ').slice(0, 3).join(' ')}...</span>
            </button>
          ))}
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {chatMessages.length === 0 && (
          <div className="text-center text-gray-500 mt-8">
            <Sparkles className="w-12 h-12 mx-auto mb-3 text-gray-400" />
            <p>Start a conversation! Ask me anything about your story.</p>
            <p className="text-sm mt-2">Try clicking one of the quick prompts above.</p>
          </div>
        )}

        {chatMessages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-4 py-3 ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-900 border border-gray-200'
              }`}
            >
              <div className="flex items-center mb-1">
                <span className="font-semibold text-sm">
                  {msg.role === 'user' ? 'You' : '✨ AI Assistant'}
                </span>
              </div>
              <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
            </div>
          </div>
        ))}

        {chatLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 border border-gray-200 rounded-lg px-4 py-3">
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-purple-600"></div>
                <span className="text-sm text-gray-600">Thinking...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={chatMessagesEndRef} />
      </div>

      {/* Chat Input */}
      <div className="border-t border-gray-200 p-4 bg-white">
        <div className="flex space-x-2">
          <textarea
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSendChat()
              }
            }}
            placeholder="Ask about your story, request suggestions, or get feedback..."
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
            rows="2"
          />
          <button
            onClick={handleSendChat}
            disabled={chatLoading || !chatInput.trim()}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </div>
  )

  const renderSynopsis = () => (
    <div className="h-full flex flex-col bg-gradient-to-b from-amber-50 to-white">
      <div className="bg-white border-b border-amber-200 px-4 py-3">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-lg font-semibold text-amber-900 flex items-center">
              <FileEdit className="w-5 h-5 mr-2" />
              Story Synopsis & Notes
            </h3>
            <p className="text-sm text-gray-600">
              Keep track of characters, plot, themes, and learning objectives
            </p>
          </div>
          <button
            onClick={handleSaveSynopsis}
            disabled={synopsisLoading || !synopsisHasChanges}
            className="px-4 py-2 bg-amber-600 text-white hover:bg-amber-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center text-sm"
          >
            {synopsisLoading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" />
                Save Synopsis
              </>
            )}
          </button>
        </div>
        <div className="flex items-center space-x-2">
          <label className="text-sm font-medium text-gray-700">File:</label>
          <select
            value={synopsisFile}
            onChange={(e) => setSynopsisFile(e.target.value)}
            className="px-3 py-1.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 text-sm"
          >
            <option value="draft_synopsis.txt">draft_synopsis.txt</option>
            <option value="synopsis.md">synopsis.md</option>
          </select>
        </div>
      </div>

      <div className="flex-1 p-4">
        <textarea
          value={synopsis}
          onChange={handleSynopsisChange}
          className="w-full h-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 font-mono text-sm resize-none"
          placeholder="# Story Synopsis&#10;&#10;## Overview&#10;&#10;## Characters&#10;&#10;## Plot Points&#10;&#10;## Themes&#10;&#10;## Learning Objectives"
        />
      </div>
    </div>
  )

  const renderProductionFormat = () => (
    <div className="h-full flex flex-col bg-gradient-to-b from-indigo-50 to-white">
      <div className="bg-white border-b border-indigo-200 px-4 py-3">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-lg font-semibold text-indigo-900 flex items-center">
              <Code className="w-5 h-5 mr-2" />
              Production Format Editor
            </h3>
            <p className="text-sm text-gray-600">
              Edit the final HTML format for your book (formatted_book.html)
            </p>
          </div>
          <button
            onClick={handleSaveFormattedBook}
            disabled={formattedLoading || !formattedHasChanges}
            className="px-4 py-2 bg-indigo-600 text-white hover:bg-indigo-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center text-sm"
          >
            {formattedLoading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" />
                Save HTML
              </>
            )}
          </button>
        </div>
        {formattedHasChanges && (
          <div className="flex items-center text-yellow-600 text-sm mt-2">
            <AlertCircle className="w-4 h-4 mr-1" />
            Unsaved changes
          </div>
        )}
      </div>

      <div className="flex-1">
        {formattedLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
          </div>
        ) : (
          <Editor
            height="100%"
            defaultLanguage="html"
            value={formattedContent}
            onChange={handleFormattedContentChange}
            theme="vs-light"
            options={{
              minimap: { enabled: true },
              fontSize: 14,
              wordWrap: 'on',
              lineNumbers: 'on',
              scrollBeyondLastLine: false,
              automaticLayout: true,
              formatOnPaste: true,
              formatOnType: true,
            }}
          />
        )}
      </div>
    </div>
  )

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Top Toolbar */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">Version</label>
              <select
                value={selectedVersion}
                onChange={(e) => setSelectedVersion(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {versions.map((version) => (
                  <option key={version} value={version}>
                    {version.replace(/_/g, ' ')}
                  </option>
                ))}
              </select>
            </div>

            {hasChanges && (
              <div className="flex items-center text-yellow-600 text-sm">
                <AlertCircle className="w-4 h-4 mr-1" />
                Unsaved changes
              </div>
            )}
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setSplitView(!splitView)}
              className={`px-4 py-2 rounded-lg flex items-center ${
                splitView
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <Eye className="w-4 h-4 mr-2" />
              Split View
            </button>

            <button
              onClick={loadStoryVersion}
              disabled={loading || !hasChanges}
              className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              <RotateCcw className="w-4 h-4 mr-2" />
              Discard
            </button>

            <button
              onClick={handleSave}
              disabled={saving || !hasChanges}
              className="px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              {saving ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Save
                </>
              )}
            </button>

            <button
              onClick={handleProcess}
              disabled={processing}
              className="px-4 py-2 bg-green-600 text-white hover:bg-green-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              {processing ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Processing...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  Run Publisher
                </>
              )}
            </button>
          </div>
        </div>

        {message && (
          <div
            className={`mt-3 p-3 rounded-lg flex items-center ${
              message.type === 'success'
                ? 'bg-green-50 text-green-800'
                : 'bg-red-50 text-red-800'
            }`}
          >
            {message.type === 'success' ? (
              <CheckCircle className="w-4 h-4 mr-2" />
            ) : (
              <AlertCircle className="w-4 h-4 mr-2" />
            )}
            {message.text}
          </div>
        )}
      </div>

      {/* Tab Navigation */}
      {!splitView && (
        <div className="bg-white border-b border-gray-200 px-6 flex space-x-1">
          <button
            onClick={() => setActivePanel('editor')}
            className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors ${
              activePanel === 'editor'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            <FileText className="w-4 h-4 inline mr-2" />
            Editor
          </button>
          <button
            onClick={() => setActivePanel('ai-chat')}
            className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors ${
              activePanel === 'ai-chat'
                ? 'border-purple-600 text-purple-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            <MessageSquare className="w-4 h-4 inline mr-2" />
            AI Chat
          </button>
          <button
            onClick={() => setActivePanel('synopsis')}
            className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors ${
              activePanel === 'synopsis'
                ? 'border-amber-600 text-amber-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            <BookOpen className="w-4 h-4 inline mr-2" />
            Synopsis
          </button>
          <button
            onClick={() => setActivePanel('production')}
            className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors ${
              activePanel === 'production'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            <Code className="w-4 h-4 inline mr-2" />
            Production Format
          </button>
          <button
            onClick={() => setActivePanel('guide')}
            className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors ${
              activePanel === 'guide'
                ? 'border-green-600 text-green-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            <HelpCircle className="w-4 h-4 inline mr-2" />
            Guide
          </button>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden">
        {splitView ? (
          <div className="h-full flex">
            <div className="flex-1 border-r border-gray-200">
              {loading ? (
                <div className="flex items-center justify-center h-full">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
                </div>
              ) : (
                <Editor
                  height="100%"
                  defaultLanguage="markdown"
                  value={content}
                  onChange={handleContentChange}
                  onMount={handleEditorMount}
                  theme="vs-light"
                  options={{
                    minimap: { enabled: true },
                    fontSize: 14,
                    wordWrap: 'on',
                    lineNumbers: 'on',
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                  }}
                />
              )}
            </div>
            <div className="w-96">
              {renderAIChat()}
            </div>
          </div>
        ) : (
          <>
            {activePanel === 'editor' && (
              loading ? (
                <div className="flex items-center justify-center h-full">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
                </div>
              ) : (
                <Editor
                  height="100%"
                  defaultLanguage="markdown"
                  value={content}
                  onChange={handleContentChange}
                  onMount={handleEditorMount}
                  theme="vs-light"
                  options={{
                    minimap: { enabled: true },
                    fontSize: 14,
                    wordWrap: 'on',
                    lineNumbers: 'on',
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                  }}
                />
              )
            )}
            {activePanel === 'ai-chat' && renderAIChat()}
            {activePanel === 'synopsis' && renderSynopsis()}
            {activePanel === 'production' && renderProductionFormat()}
            {activePanel === 'guide' && renderGuide()}
          </>
        )}
      </div>
    </div>
  )
}

export default StoryEditor
