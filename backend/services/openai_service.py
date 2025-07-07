import os
import tempfile
from typing import List, Dict, Any, Optional
from openai import OpenAI
import re
from backend.config.settings import settings
import logging

logger = logging.getLogger(__name__)


class OpenAIService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.assistant_id = settings.openai_assistant_id
        self.chunk_size = 800
        self.chunk_overlap = 200
    
    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for a list of texts"""
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-large",
                input=texts
            )
            return [embedding.embedding for embedding in response.data]
        except Exception as e:
            logger.error(f"Error creating embeddings: {e}")
            raise
    
    def create_file_embedding(self, file_path: str) -> str:
        """Upload a file to OpenAI and return the file ID"""
        try:
            with open(file_path, 'rb') as file:
                response = self.client.files.create(
                    file=file,
                    purpose="assistants"
                )
            return response.id
        except Exception as e:
            logger.error(f"Error uploading file to OpenAI: {e}")
            raise
    
    def create_assistant(self, name: str = "Resume Assistant", instructions: str = None) -> str:
        """Create an OpenAI assistant"""
        if instructions is None:
            instructions = """
            You are a resume analysis assistant. Your job is to help recruiters find the best candidates 
            by analyzing resumes and answering questions about candidates' skills, experience, and fit for roles.
            
            When asked about candidates:
            1. Analyze the provided resume information
            2. Provide clear, concise summaries
            3. Highlight relevant skills and experience
            4. Give specific examples from their background
            5. Rate their fit for the role (High/Medium/Low)
            
            Always be professional and objective in your analysis.
            """
        
        try:
            response = self.client.beta.assistants.create(
                name=name,
                instructions=instructions,
                model="gpt-4-turbo-preview",
                tools=[{"type": "retrieval"}]
            )
            return response.id
        except Exception as e:
            logger.error(f"Error creating assistant: {e}")
            raise
    
    def create_thread(self) -> str:
        """Create a new conversation thread"""
        try:
            response = self.client.beta.threads.create()
            return response.id
        except Exception as e:
            logger.error(f"Error creating thread: {e}")
            raise
    
    def add_message_to_thread(self, thread_id: str, message: str) -> str:
        """Add a message to a thread"""
        try:
            response = self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message
            )
            return response.id
        except Exception as e:
            logger.error(f"Error adding message to thread: {e}")
            raise
    
    def run_assistant(self, thread_id: str, assistant_id: str = None) -> str:
        """Run the assistant on a thread"""
        if assistant_id is None:
            assistant_id = self.assistant_id
        
        try:
            response = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=assistant_id
            )
            return response.id
        except Exception as e:
            logger.error(f"Error running assistant: {e}")
            raise
    
    def get_run_status(self, thread_id: str, run_id: str) -> str:
        """Get the status of a run"""
        try:
            response = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )
            return response.status
        except Exception as e:
            logger.error(f"Error getting run status: {e}")
            raise
    
    def get_thread_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get all messages from a thread"""
        try:
            response = self.client.beta.threads.messages.list(thread_id=thread_id)
            messages = []
            for msg in response.data:
                messages.append({
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content[0].text.value if msg.content else "",
                    "created_at": msg.created_at
                })
            return messages
        except Exception as e:
            logger.error(f"Error getting thread messages: {e}")
            raise
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks for processing"""
        # Simple text splitting by paragraphs and sentences
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) <= self.chunk_size:
                current_chunk += paragraph + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # If chunks are too large, split by sentences
        final_chunks = []
        for chunk in chunks:
            if len(chunk) <= self.chunk_size:
                final_chunks.append(chunk)
            else:
                sentences = re.split(r'[.!?]+', chunk)
                current_sentence_chunk = ""
                for sentence in sentences:
                    if len(current_sentence_chunk) + len(sentence) <= self.chunk_size:
                        current_sentence_chunk += sentence + ". "
                    else:
                        if current_sentence_chunk:
                            final_chunks.append(current_sentence_chunk.strip())
                        current_sentence_chunk = sentence + ". "
                if current_sentence_chunk:
                    final_chunks.append(current_sentence_chunk.strip())
        
        return final_chunks
    
    def analyze_resume_with_assistant(self, resume_text: str, query: str) -> Dict[str, Any]:
        """Analyze a resume using the OpenAI assistant"""
        try:
            # Create a temporary file with the resume text
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(resume_text)
                temp_file_path = f.name
            
            # Upload file to OpenAI
            file_id = self.create_file_embedding(temp_file_path)
            
            # Create or use existing assistant
            if not self.assistant_id:
                self.assistant_id = self.create_assistant()
            
            # Create thread and add message
            thread_id = self.create_thread()
            message_id = self.add_message_to_thread(thread_id, query)
            
            # Run assistant
            run_id = self.run_assistant(thread_id, self.assistant_id)
            
            # Wait for completion (in production, you'd want to implement proper polling)
            import time
            while True:
                status = self.get_run_status(thread_id, run_id)
                if status in ["completed", "failed", "cancelled"]:
                    break
                time.sleep(1)
            
            # Get response
            messages = self.get_thread_messages(thread_id)
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            
            return {
                "thread_id": thread_id,
                "run_id": run_id,
                "status": status,
                "messages": messages,
                "file_id": file_id
            }
            
        except Exception as e:
            logger.error(f"Error analyzing resume with assistant: {e}")
            raise


# Global instance
openai_service = OpenAIService() 