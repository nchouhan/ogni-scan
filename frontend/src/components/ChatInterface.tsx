import React, { useState, useRef, useEffect } from 'react'
import { Send, User, Bot, Loader2 } from 'lucide-react'
import { cn, formatDate } from '../lib/utils'

interface Message {
  id: string
  type: 'user' | 'assistant'
  content: string
  timestamp: Date
  isLoading?: boolean
}

interface ChatInterfaceProps {
  className?: string
}

export function ChatInterface({ className }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'assistant',
      content: "Hello! I'm CogniScan, your AI resume assistant. I can help you analyze resumes, search for candidates, and provide insights. What would you like to do today?",
      timestamp: new Date()
    }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: input,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    // Add loading message
    const loadingMessage: Message = {
      id: (Date.now() + 1).toString(),
      type: 'assistant',
      content: '',
      timestamp: new Date(),
      isLoading: true
    }

    setMessages(prev => [...prev, loadingMessage])

    try {
      // Simulate AI response based on user input
      const response = await generateAIResponse(input)
      setMessages(prev => prev.filter(msg => !msg.isLoading).concat({
        id: (Date.now() + 2).toString(),
        type: 'assistant',
        content: response,
        timestamp: new Date()
      }))
    } catch (error) {
      setMessages(prev => prev.filter(msg => !msg.isLoading).concat({
        id: (Date.now() + 2).toString(),
        type: 'assistant',
        content: "I'm sorry, I encountered an error. Please try again.",
        timestamp: new Date()
      }))
    } finally {
      setIsLoading(false)
    }
  }

  const generateAIResponse = async (userInput: string): Promise<string> => {
    await new Promise(resolve => setTimeout(resolve, 1000))
    return "I understand you're asking about: " + userInput + ". I can help you with resume analysis, candidate search, and insights. Could you be more specific about what you'd like to know?"
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-background rounded-t-xl border border-muted shadow-inner">
        {messages.map((message) => (
          <div
            key={message.id}
            className={cn(
              "flex gap-3",
              message.type === 'user' ? 'justify-end' : 'justify-start'
            )}
          >
            {message.type === 'assistant' && (
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                <Bot className="w-5 h-5 text-primary-foreground" />
              </div>
            )}
            <div
              className={cn(
                "max-w-[80%] rounded-xl px-4 py-2 shadow",
                message.type === 'user'
                  ? 'bg-primary text-primary-foreground ml-12'
                  : 'bg-card text-foreground mr-12 border border-muted'
              )}
            >
              {message.isLoading ? (
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Thinking...</span>
                </div>
              ) : (
                <div className="whitespace-pre-wrap">{message.content}</div>
              )}
              <div className={cn(
                "text-xs mt-1 text-muted-foreground text-right"
              )}>
                {formatDate(message.timestamp)}
              </div>
            </div>
            {message.type === 'user' && (
              <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center flex-shrink-0">
                <User className="w-5 h-5 text-secondary-foreground" />
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      {/* Input Area */}
      <div className="border-t border-muted bg-card p-4 rounded-b-xl shadow flex flex-col gap-2">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask me about resumes, candidates, or upload files..."
            className="w-full resize-none rounded-lg border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 shadow"
            rows={1}
            disabled={isLoading}
          />
          <button
            onClick={handleSendMessage}
            disabled={!input.trim() || isLoading}
            className="inline-flex items-center justify-center rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground ring-offset-background transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 shadow"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <div className="text-xs text-muted-foreground mt-1 text-right">
          Press Enter to send, Shift+Enter for new line
        </div>
      </div>
    </div>
  )
} 