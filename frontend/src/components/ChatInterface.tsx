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

// CandidateCard component for displaying candidate info in a card UI
interface Candidate {
  name: string;
  role?: string;
  company?: string;
  whyRelevant?: string;
  skills?: string[];
  experience?: string;
  relevance?: string;
  traits?: string[];
}

function CandidateCard({ candidate, highlight }: { candidate: Candidate, highlight?: boolean }) {
  return (
    <Card
      elevation={highlight ? 8 : 2}
      sx={{
        maxWidth: 420,
        mx: 'auto',
        mb: 3,
        borderRadius: 3,
        border: highlight ? '2px solid #1976d2' : '1px solid #e0e0e0',
        boxShadow: highlight ? 8 : 2,
        transition: 'box-shadow 0.2s, border 0.2s',
        position: 'relative',
        background: highlight ? 'linear-gradient(90deg, #e3f2fd 0%, #fff 100%)' : undefined
      }}
      className={highlight ? 'animate-pulse' : ''}
    >
      <CardHeader
        avatar={
          <Avatar sx={{ bgcolor: highlight ? '#1976d2' : '#673ab7', width: 48, height: 48, fontSize: 24 }}>
            {candidate.name.charAt(0)}
          </Avatar>
        }
        title={<Typography variant="h6">{candidate.name}</Typography>}
        subheader={
          <>
            <Typography variant="body2" color="text.secondary">
              {candidate.role}{candidate.company ? ` @ ${candidate.company}` : ''}
            </Typography>
            {highlight && (
              <Box display="flex" alignItems="center" gap={0.5} mt={0.5}>
                <StarIcon fontSize="small" color="primary" />
                <Typography variant="caption" color="primary.main" fontWeight={700}>Top Match</Typography>
              </Box>
            )}
          </>
        }
        sx={{ pb: 0 }}
      />
      <CardContent sx={{ pt: 1 }}>
        {candidate.whyRelevant && (
          <Typography variant="body2" color="text.primary" mb={1}>{candidate.whyRelevant}</Typography>
        )}
        {candidate.skills && candidate.skills.length > 0 && (
          <Box display="flex" flexWrap="wrap" gap={1} mb={1}>
            {candidate.skills.map(skill => (
              <Chip key={skill} label={skill} color="primary" variant="outlined" size="small" />
            ))}
          </Box>
        )}
        {candidate.traits && candidate.traits.length > 0 && (
          <Box mb={1}>
            <Typography variant="caption" color="text.secondary" fontWeight={700}>Notable Traits:</Typography>
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {candidate.traits.map(trait => <li key={trait}><Typography variant="caption">{trait}</Typography></li>)}
            </ul>
          </Box>
        )}
        {candidate.experience && (
          <Typography variant="caption" color="text.secondary">{candidate.experience}</Typography>
        )}
        {candidate.relevance && (
          <Chip
            label={`Relevance: ${candidate.relevance}`}
            color={candidate.relevance.toLowerCase().includes('high') ? 'success' : candidate.relevance.toLowerCase().includes('medium') ? 'warning' : 'default'}
            size="small"
            sx={{ mt: 1, fontWeight: 700 }}
          />
        )}
        <Box mt={2} display="flex" gap={1}>
          <Button variant="contained" color="primary" size="small">View Resume</Button>
          <Button variant="outlined" color="secondary" size="small">Shortlist</Button>
        </Box>
      </CardContent>
    </Card>
  );
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
          if (message.type === 'assistant' && !message.isLoading) {
            const candidates = extractCandidatesFromMessage(message.content);
            if (candidates && candidates.length > 0) {
              return (
                <Box key={message.id} display="flex" flexDirection="column" alignItems="center" gap={2} width="100%">
                  {candidates.map((candidate, idx) => (
                    <CandidateCard key={candidate.name + idx} candidate={candidate} highlight={idx === 0} />
                  ))}
                  <Typography variant="caption" color="text.secondary" align="right" width="100%" maxWidth={420} mt={-1}>
                    {formatDate(message.timestamp)}
                  </Typography>
                </Box>
              );
            }
          }
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
                    <span>Searching through resumes...</span>
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