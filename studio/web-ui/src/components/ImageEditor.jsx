import { useState, useEffect, useRef } from 'react'
import * as fabric from 'fabric'
import {
  X, Save, Undo, Redo, MousePointer, Square, Circle, Type,
  Pencil, Trash2, Download, ZoomIn, ZoomOut, Layers,
  Settings, Plus, Eye, EyeOff, Lock, Unlock, Image as ImageIcon, Sparkles
} from 'lucide-react'
import { ChromePicker } from 'react-color'
import axios from 'axios'

function ImageEditor({ imageUrl, imageName, onSave, onClose }) {
  const canvasRef = useRef(null)
  const [canvas, setCanvas] = useState(null)
  const [activeTool, setActiveTool] = useState('select')
  const [color, setColor] = useState('#000000')
  const [showColorPicker, setShowColorPicker] = useState(false)
  const [brushWidth, setBrushWidth] = useState(5)
  const [layers, setLayers] = useState([])
  const [selectedLayer, setSelectedLayer] = useState(null)
  const [activePanel, setActivePanel] = useState('layers')
  const [filters, setFilters] = useState({
    brightness: 0,
    contrast: 0,
    saturation: 0,
    blur: 0,
    sepia: false,
    grayscale: false,
    invert: false
  })
  const [showAiDialog, setShowAiDialog] = useState(false)
  const [aiPrompt, setAiPrompt] = useState('')
  const [aiEnhancing, setAiEnhancing] = useState(false)
  const [previousEdits, setPreviousEdits] = useState([])

  // Initialize Fabric canvas
  useEffect(() => {
    if (!canvasRef.current) return

    const fabricCanvas = new fabric.Canvas(canvasRef.current, {
      width: 1200,
      height: 800,
      backgroundColor: '#f0f0f0',
      preserveObjectStacking: true
    })

    // Load the image
    console.log('Loading image from:', imageUrl)

    fabric.FabricImage.fromURL(imageUrl, { crossOrigin: 'anonymous' })
      .then((img) => {
        console.log('Image loaded successfully:', img.width, 'x', img.height)

        const scale = Math.min(
          fabricCanvas.width / img.width,
          fabricCanvas.height / img.height
        ) * 0.9

        img.scale(scale)
        img.set({
          left: fabricCanvas.width / 2,
          top: fabricCanvas.height / 2,
          originX: 'center',
          originY: 'center',
          selectable: false,
          evented: false
        })

        // Add image first - it will be at the back by default since added first
        fabricCanvas.add(img)
        fabricCanvas.renderAll()

        updateLayers(fabricCanvas)
      })
      .catch((error) => {
        console.error('Error loading image:', error)
        alert(`Failed to load image: ${error.message || 'Unknown error'}`)
      })

    // Event handlers
    fabricCanvas.on('object:added', () => updateLayers(fabricCanvas))
    fabricCanvas.on('object:removed', () => updateLayers(fabricCanvas))
    fabricCanvas.on('object:modified', () => updateLayers(fabricCanvas))
    fabricCanvas.on('selection:created', (e) => setSelectedLayer(e.selected[0]))
    fabricCanvas.on('selection:updated', (e) => setSelectedLayer(e.selected[0]))
    fabricCanvas.on('selection:cleared', () => setSelectedLayer(null))

    setCanvas(fabricCanvas)

    return () => {
      fabricCanvas.dispose()
    }
  }, [imageUrl])

  // Update layers list
  const updateLayers = (fabricCanvas) => {
    if (!fabricCanvas) return
    const objects = fabricCanvas.getObjects()
    setLayers(objects.map((obj, idx) => ({
      id: idx,
      type: obj.type,
      name: obj.name || `${obj.type} ${idx}`,
      visible: obj.visible !== false,
      locked: obj.selectable === false && obj.evented === false,
      object: obj
    })))
  }

  // Tool handlers
  useEffect(() => {
    if (!canvas) return

    // Clear existing drawing mode
    canvas.isDrawingMode = false
    canvas.selection = true
    canvas.defaultCursor = 'default'

    switch (activeTool) {
      case 'select':
        canvas.defaultCursor = 'default'
        makeObjectsSelectable(true)
        break

      case 'pencil':
        canvas.isDrawingMode = true
        // Create and configure brush for Fabric.js v6.x
        const brush = new fabric.PencilBrush(canvas)
        brush.color = color
        brush.width = brushWidth
        canvas.freeDrawingBrush = brush
        makeObjectsSelectable(false)
        break

      case 'rectangle':
        setupShapeDrawing('rect')
        break

      case 'circle':
        setupShapeDrawing('circle')
        break

      case 'text':
        addText()
        setActiveTool('select')
        break

      default:
        break
    }
  }, [activeTool, canvas, color, brushWidth])

  const makeObjectsSelectable = (selectable) => {
    if (!canvas) return
    canvas.getObjects().forEach(obj => {
      if (obj.type !== 'image' || obj.selectable !== false) {
        obj.selectable = selectable
        obj.evented = selectable
      }
    })
  }

  const setupShapeDrawing = (shapeType) => {
    if (!canvas) return

    canvas.defaultCursor = 'crosshair'
    makeObjectsSelectable(false)

    let shape, isDrawing = false, startX, startY

    const onMouseDown = (e) => {
      isDrawing = true
      const pointer = canvas.getPointer(e.e)
      startX = pointer.x
      startY = pointer.y

      if (shapeType === 'rect') {
        shape = new fabric.Rect({
          left: startX,
          top: startY,
          width: 0,
          height: 0,
          fill: 'transparent',
          stroke: color,
          strokeWidth: 2
        })
      } else if (shapeType === 'circle') {
        shape = new fabric.Circle({
          left: startX,
          top: startY,
          radius: 0,
          fill: 'transparent',
          stroke: color,
          strokeWidth: 2
        })
      }

      canvas.add(shape)
    }

    const onMouseMove = (e) => {
      if (!isDrawing || !shape) return
      const pointer = canvas.getPointer(e.e)

      if (shapeType === 'rect') {
        shape.set({
          width: Math.abs(pointer.x - startX),
          height: Math.abs(pointer.y - startY),
          left: Math.min(startX, pointer.x),
          top: Math.min(startY, pointer.y)
        })
      } else if (shapeType === 'circle') {
        const radius = Math.sqrt(
          Math.pow(pointer.x - startX, 2) + Math.pow(pointer.y - startY, 2)
        )
        shape.set({ radius })
      }

      canvas.renderAll()
    }

    const onMouseUp = () => {
      isDrawing = false
      canvas.off('mouse:down', onMouseDown)
      canvas.off('mouse:move', onMouseMove)
      canvas.off('mouse:up', onMouseUp)
      setActiveTool('select')
    }

    canvas.on('mouse:down', onMouseDown)
    canvas.on('mouse:move', onMouseMove)
    canvas.on('mouse:up', onMouseUp)
  }

  const addText = () => {
    if (!canvas) return

    const text = new fabric.IText('Double click to edit', {
      left: canvas.width / 2,
      top: canvas.height / 2,
      fill: color,
      fontSize: 32,
      fontFamily: 'Arial'
    })

    canvas.add(text)
    canvas.setActiveObject(text)
    canvas.renderAll()
  }

  // Filter handlers
  const applyFilters = () => {
    if (!canvas) return

    const baseImage = canvas.getObjects().find(obj => obj.type === 'image')
    if (!baseImage) return

    baseImage.filters = []

    if (filters.brightness !== 0) {
      baseImage.filters.push(new fabric.filters.Brightness({
        brightness: filters.brightness / 100
      }))
    }

    if (filters.contrast !== 0) {
      baseImage.filters.push(new fabric.filters.Contrast({
        contrast: filters.contrast / 100
      }))
    }

    if (filters.saturation !== 0) {
      baseImage.filters.push(new fabric.filters.Saturation({
        saturation: filters.saturation / 100
      }))
    }

    if (filters.blur > 0) {
      baseImage.filters.push(new fabric.filters.Blur({
        blur: filters.blur / 10
      }))
    }

    if (filters.sepia) {
      baseImage.filters.push(new fabric.filters.Sepia())
    }

    if (filters.grayscale) {
      baseImage.filters.push(new fabric.filters.Grayscale())
    }

    if (filters.invert) {
      baseImage.filters.push(new fabric.filters.Invert())
    }

    baseImage.applyFilters()
    canvas.renderAll()
  }

  useEffect(() => {
    applyFilters()
  }, [filters, canvas])

  // Layer actions
  const toggleLayerVisibility = (layer) => {
    layer.object.visible = !layer.object.visible
    canvas.renderAll()
    updateLayers(canvas)
  }

  const toggleLayerLock = (layer) => {
    const newLocked = !layer.locked
    layer.object.selectable = !newLocked
    layer.object.evented = !newLocked
    updateLayers(canvas)
  }

  const deleteLayer = (layer) => {
    canvas.remove(layer.object)
    canvas.renderAll()
  }

  const deleteSelected = () => {
    const activeObject = canvas.getActiveObject()
    if (activeObject) {
      canvas.remove(activeObject)
      canvas.renderAll()
    }
  }

  // Zoom
  const zoomIn = () => {
    const zoom = canvas.getZoom()
    canvas.setZoom(zoom * 1.1)
  }

  const zoomOut = () => {
    const zoom = canvas.getZoom()
    canvas.setZoom(zoom / 1.1)
  }

  // Save
  const handleSave = () => {
    if (!canvas) return

    // Export as PNG
    const dataURL = canvas.toDataURL({
      format: 'png',
      quality: 1
    })

    onSave(dataURL, imageName)
  }

  const handleDownload = () => {
    if (!canvas) return

    const dataURL = canvas.toDataURL({
      format: 'png',
      quality: 1
    })

    const link = document.createElement('a')
    link.download = `edited_${imageName}`
    link.href = dataURL
    link.click()
  }

  const handleAiEnhance = async () => {
    if (!canvas || !aiPrompt.trim()) return

    try {
      setAiEnhancing(true)

      // Get current canvas as data URL
      const dataURL = canvas.toDataURL({
        format: 'png',
        quality: 1
      })

      // Call backend API
      const response = await axios.post('http://localhost:8000/api/media/enhance', {
        data_url: dataURL,
        prompt: aiPrompt,
        previous_edits: previousEdits
      })

      if (response.data.status === 'success') {
        // Load the enhanced image back into canvas
        fabric.FabricImage.fromURL(response.data.data_url, { crossOrigin: 'anonymous' })
          .then((img) => {
            // Clear canvas but keep dimensions
            const width = canvas.width
            const height = canvas.height
            canvas.clear()
            canvas.setDimensions({ width, height })

            // Scale and position the enhanced image
            const scale = Math.min(width / img.width, height / img.height) * 0.9
            img.scale(scale)
            img.set({
              left: width / 2,
              top: height / 2,
              originX: 'center',
              originY: 'center',
              selectable: false,
              evented: false
            })

            canvas.add(img)
            canvas.renderAll()

            // Add to edit history
            setPreviousEdits([...previousEdits, aiPrompt])
            setAiPrompt('')
            setShowAiDialog(false)
            alert('Image enhanced successfully!')
          })
          .catch((error) => {
            console.error('Error loading enhanced image:', error)
            alert('Failed to load enhanced image')
          })
      }
    } catch (error) {
      console.error('Error enhancing image:', error)
      alert(error.response?.data?.detail || 'Failed to enhance image. Please try again.')
    } finally {
      setAiEnhancing(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-gray-900 z-50 flex flex-col">
      {/* Header */}
      <div className="bg-gray-800 text-white px-4 py-3 flex items-center justify-between border-b border-gray-700">
        <div className="flex items-center gap-3">
          <ImageIcon className="w-5 h-5" />
          <h2 className="text-lg font-semibold">Image Editor - {imageName}</h2>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleDownload}
            className="px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Download
          </button>
          <button
            onClick={() => setShowAiDialog(true)}
            className="px-3 py-2 bg-purple-600 hover:bg-purple-700 rounded flex items-center gap-2"
          >
            <Sparkles className="w-4 h-4" />
            AI Enhance
          </button>
          <button
            onClick={handleSave}
            className="px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded flex items-center gap-2"
          >
            <Save className="w-4 h-4" />
            Save
          </button>
          <button
            onClick={onClose}
            className="px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Toolbar */}
        <div className="bg-gray-800 border-r border-gray-700 p-2 flex flex-col gap-2">
          <ToolButton
            icon={MousePointer}
            active={activeTool === 'select'}
            onClick={() => setActiveTool('select')}
            tooltip="Select"
          />
          <ToolButton
            icon={Pencil}
            active={activeTool === 'pencil'}
            onClick={() => setActiveTool('pencil')}
            tooltip="Draw"
          />
          <ToolButton
            icon={Square}
            active={activeTool === 'rectangle'}
            onClick={() => setActiveTool('rectangle')}
            tooltip="Rectangle"
          />
          <ToolButton
            icon={Circle}
            active={activeTool === 'circle'}
            onClick={() => setActiveTool('circle')}
            tooltip="Circle"
          />
          <ToolButton
            icon={Type}
            active={activeTool === 'text'}
            onClick={() => setActiveTool('text')}
            tooltip="Text"
          />

          <div className="border-t border-gray-700 my-2"></div>

          <ToolButton
            icon={Trash2}
            onClick={deleteSelected}
            tooltip="Delete Selected"
          />
          <ToolButton
            icon={ZoomIn}
            onClick={zoomIn}
            tooltip="Zoom In"
          />
          <ToolButton
            icon={ZoomOut}
            onClick={zoomOut}
            tooltip="Zoom Out"
          />
        </div>

        {/* Canvas Area */}
        <div className="flex-1 bg-gray-700 overflow-auto flex items-center justify-center">
          <canvas ref={canvasRef} />
        </div>

        {/* Right Panel */}
        <div className="w-80 bg-gray-800 border-l border-gray-700 flex flex-col">
          {/* Panel Tabs */}
          <div className="flex border-b border-gray-700">
            <button
              onClick={() => setActivePanel('layers')}
              className={`flex-1 px-4 py-3 flex items-center justify-center gap-2 ${
                activePanel === 'layers' ? 'bg-gray-700 text-white' : 'text-gray-400'
              }`}
            >
              <Layers className="w-4 h-4" />
              Layers
            </button>
            <button
              onClick={() => setActivePanel('properties')}
              className={`flex-1 px-4 py-3 flex items-center justify-center gap-2 ${
                activePanel === 'properties' ? 'bg-gray-700 text-white' : 'text-gray-400'
              }`}
            >
              <Settings className="w-4 h-4" />
              Properties
            </button>
          </div>

          {/* Panel Content */}
          <div className="flex-1 overflow-auto p-4">
            {activePanel === 'layers' && (
              <div>
                <h3 className="text-white font-semibold mb-3">Layers</h3>
                <div className="space-y-2">
                  {layers.slice().reverse().map((layer) => (
                    <div
                      key={layer.id}
                      className={`bg-gray-700 rounded p-2 flex items-center gap-2 ${
                        selectedLayer === layer.object ? 'ring-2 ring-blue-500' : ''
                      }`}
                    >
                      <button
                        onClick={() => toggleLayerVisibility(layer)}
                        className="text-gray-300 hover:text-white"
                      >
                        {layer.visible ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                      </button>
                      <span className="flex-1 text-sm text-white truncate">{layer.name}</span>
                      <button
                        onClick={() => toggleLayerLock(layer)}
                        className="text-gray-300 hover:text-white"
                      >
                        {layer.locked ? <Lock className="w-4 h-4" /> : <Unlock className="w-4 h-4" />}
                      </button>
                      {layer.type !== 'image' && (
                        <button
                          onClick={() => deleteLayer(layer)}
                          className="text-red-400 hover:text-red-300"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activePanel === 'properties' && (
              <div className="text-white">
                <h3 className="font-semibold mb-4">Properties</h3>

                {/* Color Picker */}
                <div className="mb-6">
                  <label className="block text-sm font-medium mb-2">Color</label>
                  <div className="relative">
                    <button
                      onClick={() => setShowColorPicker(!showColorPicker)}
                      className="w-full h-10 rounded border-2 border-gray-600"
                      style={{ backgroundColor: color }}
                    />
                    {showColorPicker && (
                      <div className="absolute z-10 mt-2">
                        <div
                          className="fixed inset-0"
                          onClick={() => setShowColorPicker(false)}
                        />
                        <ChromePicker
                          color={color}
                          onChange={(c) => setColor(c.hex)}
                        />
                      </div>
                    )}
                  </div>
                </div>

                {/* Brush Width */}
                {activeTool === 'pencil' && (
                  <div className="mb-6">
                    <label className="block text-sm font-medium mb-2">
                      Brush Width: {brushWidth}px
                    </label>
                    <input
                      type="range"
                      min="1"
                      max="50"
                      value={brushWidth}
                      onChange={(e) => setBrushWidth(Number(e.target.value))}
                      className="w-full"
                    />
                  </div>
                )}

                {/* Filters */}
                <div className="space-y-4">
                  <h4 className="font-medium text-sm">Filters & Effects</h4>

                  <div>
                    <label className="block text-sm mb-1">Brightness: {filters.brightness}</label>
                    <input
                      type="range"
                      min="-100"
                      max="100"
                      value={filters.brightness}
                      onChange={(e) => setFilters({...filters, brightness: Number(e.target.value)})}
                      className="w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-sm mb-1">Contrast: {filters.contrast}</label>
                    <input
                      type="range"
                      min="-100"
                      max="100"
                      value={filters.contrast}
                      onChange={(e) => setFilters({...filters, contrast: Number(e.target.value)})}
                      className="w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-sm mb-1">Saturation: {filters.saturation}</label>
                    <input
                      type="range"
                      min="-100"
                      max="100"
                      value={filters.saturation}
                      onChange={(e) => setFilters({...filters, saturation: Number(e.target.value)})}
                      className="w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-sm mb-1">Blur: {filters.blur}</label>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={filters.blur}
                      onChange={(e) => setFilters({...filters, blur: Number(e.target.value)})}
                      className="w-full"
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={filters.sepia}
                        onChange={(e) => setFilters({...filters, sepia: e.target.checked})}
                      />
                      <span className="text-sm">Sepia</span>
                    </label>

                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={filters.grayscale}
                        onChange={(e) => setFilters({...filters, grayscale: e.target.checked})}
                      />
                      <span className="text-sm">Grayscale</span>
                    </label>

                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={filters.invert}
                        onChange={(e) => setFilters({...filters, invert: e.target.checked})}
                      />
                      <span className="text-sm">Invert</span>
                    </label>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* AI Enhancement Dialog */}
      {showAiDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-purple-400" />
              AI Image Enhancement
            </h3>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                What would you like to improve?
              </label>
              <textarea
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                placeholder="E.g., Make the colors more vibrant, add a sunset background, improve lighting..."
                className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600 focus:border-purple-500 focus:outline-none resize-none"
                rows="4"
                disabled={aiEnhancing}
              />
            </div>

            {previousEdits.length > 0 && (
              <div className="mb-4">
                <p className="text-sm text-gray-400 mb-2">Previous edits:</p>
                <div className="space-y-1">
                  {previousEdits.map((edit, idx) => (
                    <div key={idx} className="text-xs text-gray-500 bg-gray-700 px-2 py-1 rounded">
                      {idx + 1}. {edit}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowAiDialog(false)
                  setAiPrompt('')
                }}
                className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded"
                disabled={aiEnhancing}
              >
                Cancel
              </button>
              <button
                onClick={handleAiEnhance}
                disabled={aiEnhancing || !aiPrompt.trim()}
                className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {aiEnhancing ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    Enhancing...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    Enhance
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function ToolButton({ icon: Icon, active, onClick, tooltip }) {
  return (
    <button
      onClick={onClick}
      title={tooltip}
      className={`p-3 rounded transition-colors ${
        active
          ? 'bg-blue-600 text-white'
          : 'text-gray-300 hover:bg-gray-700 hover:text-white'
      }`}
    >
      <Icon className="w-5 h-5" />
    </button>
  )
}

export default ImageEditor
