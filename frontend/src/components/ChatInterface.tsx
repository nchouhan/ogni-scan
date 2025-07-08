import React, { useState, useRef, useEffect } from 'react'
import { Send, User, Bot, Loader2 } from 'lucide-react'
import { cn, formatDate } from '../lib/utils'
import { resumeAPI } from '../lib/api'
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import CardHeader from '@mui/material/CardHeader';
import Avatar from '@mui/material/Avatar';
import Chip from '@mui/material/Chip';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import StarIcon from '@mui/icons-material/Star';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import Alert from '@mui/material/Alert';
import InfoIcon from '@mui/icons-material/Info';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import ReactMarkdown from 'react-markdown';

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

// Enhanced interfaces for structured markdown blocks
interface Candidate {
  name: string;
  role?: string;
  company?: string;
  skills?: string[];
  experience?: string;
  relevance?: string;
  whyRelevant?: string;
  traits?: string[];
}

interface TableData {
  title: string;
  headers: string[];
  rows: string[][];
}

interface InfoBlock {
  title: string;
  content: string;
  type?: 'info' | 'success' | 'warning' | 'error';
}

interface MarkdownBlock {
  type: 'candidate' | 'table' | 'info' | 'justification' | 'summary' | 'text';
  data: Candidate | TableData | InfoBlock | string;
}

// Helper to parse candidate table markdown into objects
function parseCandidateTable(markdown: string): Candidate[] {
  // Very basic parser for markdown tables
  const lines = markdown.split('\n').filter(l => l.trim().length > 0);
  const headerIdx = lines.findIndex(l => l.includes('| Name'));
  if (headerIdx === -1) return [];
  const header = lines[headerIdx].split('|').map(h => h.trim());
  const rows = [];
  for (let i = headerIdx + 2; i < lines.length; i++) {
    const cols = lines[i].split('|').map(c => c.trim());
    if (cols.length < 6) continue;
    rows.push({
      name: cols[1],
      role: cols[2],
      whyRelevant: cols[3],
      skills: cols[4].split(',').map(s => s.trim()),
      relevance: cols[5],
    });
  }
  return rows;
}

// Helper to detect and parse candidate summary blocks
function extractCandidatesFromMessage(content: string): Candidate[] | null {
  // Look for table format
  if (content.includes('| Name') && content.includes('| Skills')) {
    return parseCandidateTable(content);
  }
  // Look for markdown candidate blocks
  const candidateBlocks = content.split(/---+/g).map(b => b.trim()).filter(b => b.startsWith('### Candidate'));
  if (candidateBlocks.length > 0) {
    return candidateBlocks.map(block => {
      const nameMatch = block.match(/### Candidate \d+: ([^–\n]+)[–-]? ?([^\n]*)/);
      const name = nameMatch ? nameMatch[1].trim() : '';
      const company = nameMatch && nameMatch[2] ? nameMatch[2].trim() : '';
      const roleMatch = block.match(/\*\*Role(?: & Company)?:\*\* ([^\n]+)/);
      const role = roleMatch ? roleMatch[1].replace(/\(Implied\)/, '').trim() : '';
      const whyMatch = block.match(/\*\*Why (relevant|match):\*\* ([^\n]+)/);
      const whyRelevant = whyMatch ? whyMatch[2].trim() : '';
      const skillsMatch = block.match(/\*\*Skills?\*\*: ([^\n]+)/);
      const skills = skillsMatch ? skillsMatch[1].split(',').map(s => s.trim()) : [];
      const relevanceMatch = block.match(/\*\*Relevance score:\*\* ([^\n]+)/);
      const relevance = relevanceMatch ? relevanceMatch[1].trim() : '';
      return { name, company, role, whyRelevant, skills, relevance };
    });
  }
  // NEW: Parse numbered list format (e.g. 1. Name - Role ...)
  const numberedCandidates = [];
  const numberedRegex = /\n?\d+\.\s+([^-\n]+)\s*-\s*([^\n]*)\n([\s\S]*?)(?=\n\d+\.|$)/g;
  let match;
  while ((match = numberedRegex.exec(content)) !== null) {
    const nameCompany = match[1].trim();
    const role = match[2].trim();
    const details = match[3];
    let name = nameCompany;
    let company = '';
    // Try to split name and company if possible
    if (nameCompany.includes(' - ')) {
      [name, company] = nameCompany.split(' - ', 2).map(s => s.trim());
    } else if (nameCompany.includes('(')) {
      // e.g. Swati Kapur - Refyne (Fintech company)
      const parts = nameCompany.split('(');
      name = parts[0].trim();
      company = '(' + parts.slice(1).join('(');
    }
    // Extract whyRelevant, skills, experience, relevance
    const whyMatch = details.match(/Why (relevant|match):\s*([^\n]+)/i);
    const whyRelevant = whyMatch ? whyMatch[2].trim() : '';
    const skillsMatch = details.match(/Key Skills(?: & Experience)?:\s*([^\n]+)/i);
    const skills = skillsMatch ? skillsMatch[1].split(',').map(s => s.trim()) : [];
    const experienceMatch = details.match(/Experience:([^\n]+)/i);
    const experience = experienceMatch ? experienceMatch[1].trim() : '';
    const relevanceMatch = details.match(/Relevance Score:\s*([^\n]+)/i);
    const relevance = relevanceMatch ? relevanceMatch[1].trim() : '';
    numberedCandidates.push({ name, company, role, whyRelevant, skills, experience, relevance });
  }
  if (numberedCandidates.length > 0) return numberedCandidates;

  // Fallback: If assistant says 'No Candidates Named ... Found' but provides a summary, extract it
  const noCandidateMatch = content.match(/No Candidates Named\s+"([^"]+)"\s+Found/i);
  if (noCandidateMatch) {
    const searchName = noCandidateMatch[1];
    // Try to extract fallback candidate details from the rest of the message
    // Look for skills, experience, and relevance in the following lines
    const skillsMatch = content.match(/skills? like ([^\n]+)/i);
    const skills = skillsMatch ? skillsMatch[1].split(',').map(s => s.replace(/\band\b/g, '').trim()).filter(Boolean) : [];
    const experienceMatch = content.match(/(\d+\s+years? of experience?[^\n]*)/i);
    const experience = experienceMatch ? experienceMatch[1].trim() : '';
    const relevanceMatch = content.match(/Relevance:\s*\*\*([^\*]+)\*\*/i);
    const relevance = relevanceMatch ? relevanceMatch[1].trim() : 'Medium';
    const whyMatch = content.match(/\*\*Reason:\*\* ([^\n]+)/i);
    const whyRelevant = whyMatch ? whyMatch[1].trim() : 'No direct name match, but similar profile found.';
    // Try to extract role/company from the summary if present
    let role = '';
    let company = '';
    const roleCompanyMatch = content.match(/in software development, which includes skills like[^\n]*\n?([^\n]*)/i);
    if (roleCompanyMatch) {
      // Sometimes the next line after skills is the role/company
      [role, company] = roleCompanyMatch[1].split(' at ');
      role = role ? role.trim() : '';
      company = company ? company.trim() : '';
    }
    return [{
      name: searchName,
      role,
      company,
      whyRelevant,
      skills,
      experience,
      relevance
    }];
  }
  return null;
}



// Parse structured markdown into blocks
function parseStructuredMarkdown(content: string): MarkdownBlock[] {
  const blocks: MarkdownBlock[] = [];
  
  // Split by markdown headers
  const sections = content.split(/^###\s+/m);
  
  sections.forEach(section => {
    const trimmedSection = section.trim();
    if (!trimmedSection) return;
    
    if (trimmedSection.startsWith('CANDIDATE:')) {
      const candidate = parseCandidateBlock(trimmedSection);
      if (candidate) {
        blocks.push({ type: 'candidate', data: candidate });
      }
    } else if (trimmedSection.startsWith('TABLE:')) {
      const table = parseTableBlock(trimmedSection);
      if (table) {
        blocks.push({ type: 'table', data: table });
      }
    } else if (trimmedSection.startsWith('INFO:')) {
      const info = parseInfoBlock(trimmedSection);
      if (info) {
        blocks.push({ type: 'info', data: info });
      }
    } else if (trimmedSection.startsWith('JUSTIFICATION:')) {
      const info = parseInfoBlock(trimmedSection);
      if (info) {
        blocks.push({ type: 'justification', data: info });
      }
    } else if (trimmedSection.startsWith('SUMMARY:')) {
      const info = parseInfoBlock(trimmedSection);
      if (info) {
        blocks.push({ type: 'summary', data: info });
      }
    } else {
      // Regular text content
      blocks.push({ type: 'text', data: trimmedSection });
    }
  });
  
  return blocks;
}

// Parse candidate block
function parseCandidateBlock(content: string): Candidate | null {
  const lines = content.split('\n');
  const candidate: Candidate = { name: '' };
  
  lines.forEach(line => {
    const trimmed = line.trim();
    if (trimmed.startsWith('CANDIDATE:')) {
      candidate.name = trimmed.replace('CANDIDATE:', '').trim();
    } else if (trimmed.startsWith('**Role:**')) {
      candidate.role = trimmed.replace('**Role:**', '').trim();
    } else if (trimmed.startsWith('**Company:**')) {
      candidate.company = trimmed.replace('**Company:**', '').trim();
    } else if (trimmed.startsWith('**Skills:**')) {
      const skills = trimmed.replace('**Skills:**', '').trim();
      candidate.skills = skills.split(',').map(s => s.trim()).filter(s => s);
    } else if (trimmed.startsWith('**Experience:**')) {
      candidate.experience = trimmed.replace('**Experience:**', '').trim();
    } else if (trimmed.startsWith('**Relevance:**')) {
      candidate.relevance = trimmed.replace('**Relevance:**', '').trim();
    } else if (trimmed.startsWith('**Why Relevant:**')) {
      candidate.whyRelevant = trimmed.replace('**Why Relevant:**', '').trim();
    }
  });
  
  return candidate.name ? candidate : null;
}

// Parse table block
function parseTableBlock(content: string): TableData | null {
  const lines = content.split('\n');
  const table: TableData = { title: '', headers: [], rows: [] };
  
  lines.forEach((line, index) => {
    const trimmed = line.trim();
    if (trimmed.startsWith('TABLE:')) {
      table.title = trimmed.replace('TABLE:', '').trim();
    } else if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      const cells = trimmed.split('|').map(cell => cell.trim()).filter(cell => cell);
      if (index === 1) { // Header row
        table.headers = cells;
      } else if (index > 2 && cells.length > 0) { // Data rows (skip separator)
        table.rows.push(cells);
      }
    }
  });
  
  return table.headers.length > 0 ? table : null;
}

// Parse info block
function parseInfoBlock(content: string): InfoBlock | null {
  const lines = content.split('\n');
  const info: InfoBlock = { title: '', content: '' };
  
  lines.forEach((line, index) => {
    const trimmed = line.trim();
    if (trimmed.startsWith('INFO:') || trimmed.startsWith('JUSTIFICATION:') || trimmed.startsWith('SUMMARY:')) {
      info.title = trimmed.replace(/^(INFO|JUSTIFICATION|SUMMARY):/, '').trim();
    } else if (index > 0 && trimmed) {
      info.content += (info.content ? '\n' : '') + trimmed;
    }
  });
  
  return info.title ? info : null;
}

// Enhanced Candidate Card Component
function CandidateCard({ candidate, highlight }: { candidate: Candidate, highlight?: boolean }) {
  const getRelevanceColor = (relevance?: string) => {
    switch (relevance?.toLowerCase()) {
      case 'high': return 'success';
      case 'medium': return 'warning';
      case 'low': return 'error';
      default: return 'default';
    }
  };

  return (
    <Card
      elevation={highlight ? 8 : 2}
      sx={{
        maxWidth: 450,
        mb: 2,
        border: highlight ? '2px solid #1976d2' : '1px solid #e0e0e0',
        backgroundColor: highlight ? '#f3f8ff' : 'white',
        animation: highlight ? 'pulse 2s infinite' : 'none',
        '@keyframes pulse': {
          '0%': { boxShadow: '0 0 0 0 rgba(25, 118, 210, 0.7)' },
          '70%': { boxShadow: '0 0 0 10px rgba(25, 118, 210, 0)' },
          '100%': { boxShadow: '0 0 0 0 rgba(25, 118, 210, 0)' }
        }
      }}
    >
      <CardHeader
        avatar={
          <Avatar sx={{ bgcolor: highlight ? '#1976d2' : '#666' }}>
            {candidate.name.split(' ').map(n => n[0]).join('').toUpperCase()}
          </Avatar>
        }
        title={
          <Box display="flex" alignItems="center" gap={1}>
            <Typography variant="h6">{candidate.name}</Typography>
            {highlight && <StarIcon color="primary" />}
          </Box>
        }
        subheader={
          <Box>
            {candidate.role && <Typography variant="body2" color="text.secondary">{candidate.role}</Typography>}
            {candidate.company && <Typography variant="body2" color="text.secondary">{candidate.company}</Typography>}
          </Box>
        }
        action={
          candidate.relevance && (
            <Chip
              label={candidate.relevance}
              color={getRelevanceColor(candidate.relevance) as any}
              size="small"
              variant="outlined"
            />
          )
        }
      />
      <CardContent>
        {candidate.skills && candidate.skills.length > 0 && (
          <Box mb={2}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Skills:
            </Typography>
            <Box display="flex" flexWrap="wrap" gap={0.5}>
              {candidate.skills.map((skill, index) => (
                <Chip
                  key={index}
                  label={skill}
                  size="small"
                  variant="outlined"
                  color="primary"
                />
              ))}
            </Box>
          </Box>
        )}
        
        {candidate.experience && (
          <Box mb={2}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Experience:
            </Typography>
            <Typography variant="body2">{candidate.experience}</Typography>
          </Box>
        )}
        
        {candidate.whyRelevant && (
          <Box mb={2}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Why Relevant:
            </Typography>
            <Typography variant="body2">{candidate.whyRelevant}</Typography>
          </Box>
        )}
        
        <Box display="flex" gap={1} mt={2}>
          <Button variant="outlined" size="small" color="primary">
            View Resume
          </Button>
          <Button variant="contained" size="small" color="primary">
            Shortlist
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
}

// Table Component
function DataTable({ table }: { table: TableData }) {
  return (
    <Box mb={3}>
      <Typography variant="h6" gutterBottom>
        {table.title}
      </Typography>
      <TableContainer component={Paper} elevation={2}>
        <Table>
          <TableHead>
            <TableRow>
              {table.headers.map((header, index) => (
                <TableCell key={index} sx={{ fontWeight: 'bold' }}>
                  {header}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {table.rows.map((row, rowIndex) => (
              <TableRow key={rowIndex}>
                {row.map((cell, cellIndex) => (
                  <TableCell key={cellIndex}>
                    {cell}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}

// Info Block Component
function InfoBlock({ info, type }: { info: InfoBlock, type: string }) {
  const getIcon = () => {
    switch (type) {
      case 'justification':
        return <CheckCircleIcon />;
      case 'summary':
        return <InfoIcon />;
      default:
        return <InfoIcon />;
    }
  };

  const getSeverity = () => {
    switch (info.type) {
      case 'success': return 'success';
      case 'warning': return 'warning';
      case 'error': return 'error';
      default: return 'info';
    }
  };

  return (
    <Alert 
      severity={getSeverity() as any}
      icon={getIcon()}
      sx={{ mb: 2 }}
    >
      <Typography variant="h6" gutterBottom>
        {info.title}
      </Typography>
      <Typography variant="body2" component="div">
        {info.content.split('\n').map((line, index) => (
          <div key={index}>{line}</div>
        ))}
      </Typography>
    </Alert>
  );
}

// Render markdown blocks
function renderMarkdownBlocks(blocks: MarkdownBlock[]) {
  return blocks.map((block, index) => {
    switch (block.type) {
      case 'candidate':
        return (
          <CandidateCard 
            key={index} 
            candidate={block.data as Candidate}
            highlight={index === 0} // Highlight first candidate
          />
        );
      case 'table':
        return <DataTable key={index} table={block.data as TableData} />;
      case 'info':
      case 'justification':
      case 'summary':
        // Render info/justification/summary as markdown
        return (
          <Box key={index} mb={2}>
            <ReactMarkdown>{(block.data as InfoBlock).content}</ReactMarkdown>
          </Box>
        );
      case 'text':
        return (
          <Box key={index} mb={2}>
            <ReactMarkdown>{block.data as string}</ReactMarkdown>
          </Box>
        );
      default:
        return null;
    }
  });
}

// Update the message rendering logic
function renderMessage(message: Message) {
  if (message.type === 'assistant' && !message.isLoading) {
    // Try to parse as structured markdown first
    const blocks = parseStructuredMarkdown(message.content);
    
    if (blocks.length > 0) {
      return (
        <Box sx={{ p: 2 }}>
          {renderMarkdownBlocks(blocks)}
        </Box>
      );
    }
    
    // Fallback to existing candidate parsing for backward compatibility
    const candidates = extractCandidatesFromMessage(message.content);
    if (candidates && candidates.length > 0) {
      return (
        <Box sx={{ p: 2 }}>
          {candidates.map((candidate, index) => (
            <CandidateCard 
              key={index} 
              candidate={candidate}
              highlight={index === 0}
            />
          ))}
        </Box>
      );
    }
  }
  
  // Default text rendering
  return (
    <Typography 
      variant="body1" 
      sx={{ 
        p: 2, 
        whiteSpace: 'pre-wrap',
        backgroundColor: message.type === 'user' ? '#f5f5f5' : 'transparent',
        borderRadius: 1,
        fontWeight: 400,
        fontSize: '0.95rem',
        lineHeight: 1.5,
        color: '#333'
      }}
    >
      {message.content}
    </Typography>
  );
}



export function ChatInterface({ className }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'assistant',
      content: "👋 **Welcome to CogniScan!**\n\nI'm your AI resume assistant. I can help you:\n\n🔍 **Search candidates** - Try: 'Find Supriya' or 'Search Python developers'\n📄 **Analyze resumes** - Extract skills, experience, and qualifications\n📊 **Get insights** - Compare candidates and identify top skills\n\n**Quick start:**\n1. Upload resumes using the 'Upload Resumes' tab\n2. Ask me to search: 'Find candidates named [name]'\n3. Or search by skills: 'Who knows React?'\n\nWhat would you like to search for?",
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
    const userInput = input
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
      // Generate AI response based on user input with actual backend calls
      const response = await generateAIResponse(userInput)
      setMessages(prev => prev.filter(msg => !msg.isLoading).concat({
        id: (Date.now() + 2).toString(),
        type: 'assistant',
        content: response,
        timestamp: new Date()
      }))
    } catch (error) {
      console.error('Error generating response:', error)
      setMessages(prev => prev.filter(msg => !msg.isLoading).concat({
        id: (Date.now() + 2).toString(),
        type: 'assistant',
        content: "I'm sorry, I encountered an error while searching. Please try again.",
        timestamp: new Date()
      }))
    } finally {
      setIsLoading(false)
    }
  }

  const generateAIResponse = async (userInput: string): Promise<string> => {
    try {
      // Use OpenAI Assistant for all queries
      const chatResult = await resumeAPI.chat(userInput)
      
      if (chatResult.status === 'completed' && chatResult.response) {
        return chatResult.response
      } else {
        return "I'm having trouble processing your request right now. Please try again or rephrase your question."
      }
      
    } catch (error: any) {
      console.error('Error in generateAIResponse:', error)
      
      // Handle specific error cases
      if (error.response?.status === 401) {
        return `🔒 **Authentication Required**\n\nYou need to be logged in to search resumes. Please:\n1. Make sure you're logged in as admin\n2. Check if your session has expired\n3. Try refreshing the page\n\nIf you're still having issues, please log in again.`
      }
      
      if (error.response?.status === 404) {
        return `📂 **No Resumes Found**\n\nIt looks like no resumes have been uploaded yet. To get started:\n1. Go to the "Upload Resumes" tab\n2. Upload some PDF, DOCX, or TXT resume files\n3. Wait for them to be processed\n4. Then come back and search!\n\nOnce you have resumes uploaded, I'll be able to search through them for you.`
      }
      
      if (error.code === 'ECONNREFUSED' || error.message?.includes('Network Error')) {
        return `🔌 **Backend Connection Issue**\n\nI can't connect to the CogniScan backend service. Please:\n1. Make sure the backend server is running\n2. Check if it's accessible at http://localhost:8000\n3. Verify your network connection\n\nIf you're a developer, run the backend with: \`python3 -m uvicorn backend.main:app --reload\``
      }
      
      return `❌ **Unexpected Error**\n\nI encountered an error while processing your request:\n\n**Error:** ${error.message || 'Unknown error'}\n\nPlease try:\n• Refreshing the page\n• Rephrasing your question\n• Checking your internet connection\n• Verifying the backend service is running`
    }
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
        {messages.map((message) => {
          return (
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
              {message.type === 'user' ? (
                <Box
                  sx={{
                    maxWidth: '80%',
                    background: '#fff',
                    color: '#333',
                    borderRadius: 3,
                    border: '1px solid #1976d2',
                    px: 3,
                    py: 2,
                    boxShadow: 1,
                    ml: 6,
                    fontSize: '1rem',
                    fontWeight: 400,
                    letterSpacing: 0.1,
                    wordBreak: 'break-word',
                  }}
                >
                  <Typography variant="body1" sx={{ color: '#333', fontWeight: 400 }}>
                    {message.content}
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#888', display: 'block', mt: 1, textAlign: 'right', fontWeight: 300, fontSize: '0.75rem' }}>
                    {formatDate(message.timestamp)}
                  </Typography>
                </Box>
              ) : (
                <div
                  className={cn(
                    "max-w-[80%] rounded-xl px-4 py-2 shadow-sm",
                    'bg-card text-foreground mr-12 border border-muted'
                  )}
                  style={{
                    fontSize: '0.95rem',
                    fontWeight: 400,
                    lineHeight: 1.5
                  }}
                >
                  {message.isLoading ? (
                    <div className="flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Searching through resumes...</span>
                    </div>
                  ) : (
                    renderMessage(message)
                  )}
                  <div className={cn(
                    "text-xs mt-1 text-muted-foreground text-right"
                  )}
                  style={{
                    fontSize: '0.75rem',
                    fontWeight: 300
                  }}>
                    {formatDate(message.timestamp)}
                  </div>
                </div>
              )}
              {message.type === 'user' && (
                <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center flex-shrink-0">
                  <User className="w-5 h-5 text-secondary-foreground" />
                </div>
              )}
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>
      {/* Input Area */}
      <div className="border-t border-muted bg-card p-4 rounded-b-xl shadow flex flex-col gap-2">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask me about candidates: 'Find Supriya', 'Search Python developers', 'Who has React experience?'"
            className="w-full resize-none rounded-lg border border-input bg-white px-3 py-2 text-sm text-black placeholder:text-gray-500 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 shadow"
            style={{ color: '#000', backgroundColor: '#fff', fontWeight: 400, fontSize: '0.95rem' }}
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
        <div className="text-xs text-muted-foreground mt-1 text-right" style={{ fontWeight: 300 }}>
          Press Enter to send, Shift+Enter for new line
        </div>
      </div>
    </div>
  )
} 