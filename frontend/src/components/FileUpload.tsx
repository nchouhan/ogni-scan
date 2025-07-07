import React, { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { cn, formatFileSize } from '../lib/utils'
import { resumeAPI } from '../lib/api'
import type { Resume } from '../lib/api'

interface FileUploadProps {
  onUploadSuccess?: (resume: Resume) => void
  onUploadError?: (error: string) => void
  className?: string
}

interface UploadedFile {
  id: string
  file: File
  status: 'uploading' | 'success' | 'error'
  progress?: number
  error?: string
  resume?: Resume
}

export function FileUpload({ onUploadSuccess, onUploadError, className }: FileUploadProps) {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([])

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const newFiles: UploadedFile[] = acceptedFiles.map(file => ({
      id: Math.random().toString(36).substr(2, 9),
      file,
      status: 'uploading' as const
    }))

    setUploadedFiles(prev => [...prev, ...newFiles])

    // Upload each file
    for (const fileData of newFiles) {
      try {
        const resume = await resumeAPI.upload(fileData.file)
        
        setUploadedFiles(prev => prev.map(f => 
          f.id === fileData.id 
            ? { ...f, status: 'success' as const, resume }
            : f
        ))

        onUploadSuccess?.(resume)
      } catch (error) {
        console.error('Upload error:', error)
        const errorMessage = error instanceof Error ? error.message : 'Upload failed'
        
        setUploadedFiles(prev => prev.map(f => 
          f.id === fileData.id 
            ? { ...f, status: 'error' as const, error: errorMessage }
            : f
        ))

        onUploadError?.(errorMessage)
      }
    }
  }, [onUploadSuccess, onUploadError])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt']
    },
    maxSize: 10 * 1024 * 1024, // 10MB
    multiple: true
  })

  const removeFile = (id: string) => {
    setUploadedFiles(prev => prev.filter(f => f.id !== id))
  }

  const getStatusIcon = (status: UploadedFile['status']) => {
    switch (status) {
      case 'uploading':
        return <Loader2 className="w-4 h-4 animate-spin" />
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />
    }
  }

  const getStatusText = (status: UploadedFile['status']) => {
    switch (status) {
      case 'uploading':
        return 'Uploading...'
      case 'success':
        return 'Uploaded successfully'
      case 'error':
        return 'Upload failed'
    }
  }

  return (
    <div className={cn("space-y-4", className)}>
      {/* Drop Zone */}
      <div
        {...getRootProps()}
        className={cn(
          "border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors bg-card border-muted shadow hover:border-primary/60 hover:bg-muted/40",
          isDragActive && "border-primary bg-primary/10"
        )}
      >
        <input {...getInputProps()} />
        <Upload className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
        <h3 className="text-lg font-semibold mb-2">
          {isDragActive ? 'Drop files here' : 'Upload Resumes'}
        </h3>
        <p className="text-sm text-muted-foreground mb-4">
          Drag and drop PDF, DOCX, or TXT files here, or click to browse
        </p>
        <div className="text-xs text-muted-foreground">
          Maximum file size: 10MB • Supported formats: PDF, DOCX, TXT
        </div>
      </div>

      {/* Uploaded Files List */}
      {uploadedFiles.length > 0 && (
        <div className="space-y-2">
          <h4 className="font-medium">Uploaded Files</h4>
          {uploadedFiles.map((fileData) => (
            <div
              key={fileData.id}
              className="flex items-center justify-between p-3 bg-muted rounded-lg animate-fade-in border border-muted shadow"
            >
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <FileText className="w-5 h-5 text-muted-foreground flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="font-medium truncate">{fileData.file.name}</div>
                  <div className="text-sm text-muted-foreground">
                    {formatFileSize(fileData.file.size)}
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1 text-sm">
                  {getStatusIcon(fileData.status)}
                  <span className={cn(
                    fileData.status === 'error' ? 'text-red-600' : 
                    fileData.status === 'success' ? 'text-green-600' : 
                    'text-muted-foreground'
                  )}>
                    {getStatusText(fileData.status)}
                  </span>
                </div>
                
                <button
                  onClick={() => removeFile(fileData.id)}
                  className="p-1 hover:bg-muted-foreground/20 rounded transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Error Messages */}
      {uploadedFiles.some(f => f.status === 'error') && (
        <div className="p-3 bg-destructive/10 border border-destructive rounded-lg">
          <div className="flex items-center gap-2 text-destructive">
            <AlertCircle className="w-4 h-4" />
            <span className="font-medium">Some uploads failed</span>
          </div>
          <div className="text-sm text-destructive mt-1">
            Check your file format and size, then try again.
          </div>
        </div>
      )}
    </div>
  )
} 