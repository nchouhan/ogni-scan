import React, { useState, useEffect } from 'react'
import { Menu, X, Upload, MessageSquare, FileText, LogOut, User, Moon, Sun } from 'lucide-react'
import { ChatInterface } from './components/ChatInterface'
import { FileUpload } from './components/FileUpload'
import { cn } from './lib/utils'
import { authAPI } from './lib/api'
import type { Resume } from './lib/api'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<'chat' | 'upload' | 'resumes'>('chat')
  const [username, setUsername] = useState('')
  const [darkMode, setDarkMode] = useState(false)

  useEffect(() => {
    checkAuth()
    // Set dark mode from localStorage
    if (localStorage.getItem('cogni_dark') === 'true') {
      document.documentElement.classList.add('dark')
      setDarkMode(true)
    }
  }, [])

  const checkAuth = async () => {
    try {
      const token = localStorage.getItem('cogni_token')
      if (token) {
        const user = await authAPI.getCurrentUser()
        setUsername(user.username)
        setIsAuthenticated(true)
      }
    } catch (error) {
      console.error('Auth check failed:', error)
      localStorage.removeItem('cogni_token')
    } finally {
      setIsLoading(false)
    }
  }

  const handleLogin = async () => {
    try {
      const response = await authAPI.login({ username: 'admin', password: 'admin' })
      localStorage.setItem('cogni_token', response.access_token)
      setUsername(response.username)
      setIsAuthenticated(true)
    } catch (error) {
      console.error('Login failed:', error)
      alert('Login failed. Please check your credentials.')
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('cogni_token')
    setIsAuthenticated(false)
    setUsername('')
  }

  const handleUploadSuccess = (resume: Resume) => {
    console.log('Resume uploaded successfully:', resume)
  }

  const handleUploadError = (error: string) => {
    console.error('Upload error:', error)
  }

  const toggleDarkMode = () => {
    setDarkMode((prev) => {
      const next = !prev
      if (next) {
        document.documentElement.classList.add('dark')
      } else {
        document.documentElement.classList.remove('dark')
      }
      localStorage.setItem('cogni_dark', next ? 'true' : 'false')
      return next
    })
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background text-foreground">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading CogniScan...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background text-foreground">
        <div className="w-full max-w-md p-6">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold bg-gradient-to-r from-primary to-purple-600 bg-clip-text text-transparent">
              CogniScan
            </h1>
            <p className="text-muted-foreground mt-2">Resume Insight Assistant</p>
          </div>
          <div className="bg-card border rounded-lg p-6 shadow-xl">
            <h2 className="text-xl font-semibold mb-4">Welcome Back</h2>
            <p className="text-muted-foreground mb-6">
              Sign in to access your resume management dashboard
            </p>
            <button
              onClick={handleLogin}
              className="w-full bg-primary text-primary-foreground py-2 px-4 rounded-lg hover:bg-primary/90 transition-colors"
            >
              Sign In with Admin
            </button>
            <div className="mt-4 text-xs text-muted-foreground text-center">
              Default credentials: admin / admin
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Header */}
      <header className="border-b bg-card shadow-sm sticky top-0 z-10">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="lg:hidden p-2 hover:bg-muted rounded-lg"
            >
              {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
            <h1 className="text-xl font-bold bg-gradient-to-r from-primary to-purple-600 bg-clip-text text-transparent">
              CogniScan
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={toggleDarkMode}
              className="p-2 rounded-lg hover:bg-muted transition-colors"
              title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
            <div className="hidden sm:flex items-center gap-2 text-sm text-muted-foreground">
              <User className="w-4 h-4" />
              <span>{username}</span>
            </div>
            <button
              onClick={handleLogout}
              className="p-2 hover:bg-muted rounded-lg transition-colors"
              title="Logout"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>
      <div className="flex flex-1 min-h-0">
        {/* Sidebar */}
        <aside className={cn(
          "w-64 bg-card border-r border-muted flex-shrink-0 transform transition-transform duration-200 ease-in-out lg:translate-x-0 lg:static lg:inset-0 z-20 shadow-sm",
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}>
          <nav className="p-4 space-y-2">
            <button
              onClick={() => setActiveTab('chat')}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors",
                activeTab === 'chat'
                  ? "bg-primary text-primary-foreground shadow"
                  : "hover:bg-muted"
              )}
            >
              <MessageSquare className="w-5 h-5" />
              <span>Chat Assistant</span>
            </button>
            <button
              onClick={() => setActiveTab('upload')}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors",
                activeTab === 'upload'
                  ? "bg-primary text-primary-foreground shadow"
                  : "hover:bg-muted"
              )}
            >
              <Upload className="w-5 h-5" />
              <span>Upload Resumes</span>
            </button>
            <button
              onClick={() => setActiveTab('resumes')}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors",
                activeTab === 'resumes'
                  ? "bg-primary text-primary-foreground shadow"
                  : "hover:bg-muted"
              )}
            >
              <FileText className="w-5 h-5" />
              <span>Resume Library</span>
            </button>
          </nav>
        </aside>
        {/* Main Content */}
        <main className="flex-1 flex flex-col bg-background">
          <div className="flex-1 flex flex-col p-4 md:p-8 max-w-4xl mx-auto w-full">
            {activeTab === 'chat' && (
              <ChatInterface className="flex-1" />
            )}
            {activeTab === 'upload' && (
              <div className="flex-1 p-6 overflow-y-auto">
                <div className="max-w-2xl mx-auto">
                  <h2 className="text-2xl font-bold mb-6">Upload Resumes</h2>
                  <FileUpload onUploadSuccess={handleUploadSuccess} onUploadError={handleUploadError} />
                </div>
              </div>
            )}
            {activeTab === 'resumes' && (
              <div className="flex-1 p-6 overflow-y-auto">
                <div className="max-w-2xl mx-auto">
                  <h2 className="text-2xl font-bold mb-6">Resume Library</h2>
                  <div className="text-muted-foreground">Coming soon...</div>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}

export default App
