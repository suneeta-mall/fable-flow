import { useState, useEffect, useRef } from 'react'

export function useWebSocket(url) {
  const [messages, setMessages] = useState([])
  const [isConnected, setIsConnected] = useState(false)
  const ws = useRef(null)

  useEffect(() => {
    ws.current = new WebSocket(url)

    ws.current.onopen = () => {
      setIsConnected(true)
      console.log('WebSocket connected')
    }

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        setMessages((prev) => [...prev, data])
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }

    ws.current.onclose = () => {
      setIsConnected(false)
      console.log('WebSocket disconnected')
    }

    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    return () => {
      if (ws.current) {
        ws.current.close()
      }
    }
  }, [url])

  const sendMessage = (message) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message))
    }
  }

  return { messages, isConnected, sendMessage }
}
