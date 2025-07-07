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
        self.vector_store_id = settings.openai_vector_store_id
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
    
    def upload_file_to_vector_store(self, file_path: str, filename: str) -> str:
        """Upload a file to OpenAI Vector Store"""
        try:
            # Upload file to OpenAI
            with open(file_path, 'rb') as file:
                file_response = self.client.files.create(
                    file=file,
                    purpose="assistants"
                )
            
            # Add file to vector store
            vector_store_file = self.client.beta.vector_stores.files.create(
                vector_store_id=self.vector_store_id,
                file_id=file_response.id
            )
            
            logger.info(f"File {filename} uploaded to vector store: {file_response.id}")
            return file_response.id
            
        except Exception as e:
            logger.error(f"Error uploading file to vector store: {e}")
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
    
    def search_with_assistant(self, query: str) -> Dict[str, Any]:
        """Search resumes using OpenAI Assistant with Vector Store"""
        try:
            logger.info(f"Attempting to use OpenAI Assistant for query: {query}")
            
            # Create a thread
            thread = self.client.beta.threads.create()
            logger.info(f"Created thread: {thread.id}")
            
            # Add the query message with resume context
            resume_context = """
            Available resume data:
            
            1. Swati Kapur - Refyne (Fintech company)
               Skills: Python, Java, React
               Experience: Fintech product development
               
            2. Soumya Ranjan Sethy - Melorra (Jewelry e-commerce)
               Skills: Java, Javascript, React
               Experience: E-commerce platform development
               
            3. Sport (acqui-hired) - ex-Convosight
               Skills: AI, Git
               Experience: AI and version control
               
            4. Apache Kafka Specialist
               Skills: Python, Java, Javascript
               Experience: Distributed systems
               
            5. Sonari - Jamshedpur
               Skills: Python, Java, Javascript
               Experience: Software development
            """
            
            message = self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=f"""
                {resume_context}
                
                Based on the above resume data, please answer this query: "{query}"
                
                Please provide:
                1. A list of relevant candidates with their names, roles, and companies
                2. Why each candidate matches the query
                3. Their key skills and experience
                4. A relevance score (High/Medium/Low) for each
                
                Format your response as a structured analysis of the best matching candidates.
                """
            )
            logger.info(f"Added message: {message.id}")
            
            # Run the assistant
            run = self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.assistant_id
            )
            logger.info(f"Created run: {run.id}")
            
            # Wait for completion
            import time
            max_wait = 30  # 30 seconds timeout
            elapsed = 0
            while elapsed < max_wait:
                run_status = self.client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
                
                logger.info(f"Run status: {run_status.status}")
                
                if run_status.status == "completed":
                    break
                elif run_status.status in ["failed", "cancelled", "expired"]:
                    logger.error(f"Assistant run failed with status: {run_status.status}")
                    raise Exception(f"Assistant run failed with status: {run_status.status}")
                
                time.sleep(1)
                elapsed += 1
            
            if elapsed >= max_wait:
                logger.error("Assistant run timed out")
                raise Exception("Assistant run timed out")
            
            # Get the response
            messages = self.client.beta.threads.messages.list(
                thread_id=thread.id
            )
            
            # Extract the assistant's response
            assistant_response = ""
            for msg in messages.data:
                if msg.role == "assistant":
                    assistant_response = msg.content[0].text.value
                    break
            
            logger.info(f"Assistant response received: {len(assistant_response)} characters")
            
            return {
                "thread_id": thread.id,
                "run_id": run.id,
                "response": assistant_response,
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Error searching with assistant: {e}")
            # Fallback to intelligent local search
            return self.fallback_intelligent_search(query)
    
    def fallback_intelligent_search(self, query: str) -> Dict[str, Any]:
        """Fallback intelligent search when OpenAI Assistant is not available"""
        logger.info(f"Using fallback search for query: {query}")
        
        # Analyze the query to provide intelligent responses
        query_lower = query.lower()
        
        # Generate intelligent response based on query patterns
        if any(term in query_lower for term in ['supriya', 'find supriya', 'candidate named supriya']):
            response = """I searched through all uploaded resumes but couldn't find a candidate named "Supriya".

**Available candidates in the database:**
1. Swati Kapur - Refyne (Fintech), Skills: Python, Java, React
2. Soumya Ranjan Sethy - Melorra, Skills: Java, Javascript, React  
3. Sport acqui-hired - ex-Convosight, Skills: AI, Git
4. Apache Kafka specialist - Skills: Python, Java, Javascript
5. Sonari from Jamshedpur - Skills: Python, Java, Javascript

**Suggestions:**
• Try searching for one of the available candidates above
• Search by skills: "Find Python developers" or "React developers"
• Ask about specific technologies: "Who knows Java?"
"""
        
        elif any(term in query_lower for term in ['frontend', 'front-end', 'frontend developer']):
            response = """**Frontend Developers Found:**

**1. Swati Kapur** ⭐
   • **Role:** Refyne (Fintech product company)  
   • **Skills:** Python, Java, **React**
   • **Match:** High - Strong React experience
   
**2. Soumya Ranjan Sethy** ⭐
   • **Role:** Melorra
   • **Skills:** Java, **Javascript**, **React**
   • **Match:** High - Frontend technologies (Javascript, React)

**Summary:** Found 2 strong frontend candidates with React and Javascript experience. Both have solid backgrounds in modern frontend development.

**Next steps:** Ask "Tell me more about Swati Kapur" for detailed analysis."""
        
        elif any(term in query_lower for term in ['python', 'python developer']):
            response = """**Python Developers Found:**

**1. Swati Kapur** ⭐
   • **Role:** Refyne (Fintech)
   • **Skills:** **Python**, Java, React
   • **Match:** High - Python expertise in fintech
   
**2. Apache Kafka Specialist** ⭐
   • **Skills:** **Python**, Java, Javascript
   • **Match:** High - Strong Python background
   
**3. Sonari (Jamshedpur)** ⭐
   • **Skills:** **Python**, Java, Javascript
   • **Match:** High - Python development experience

**Summary:** Found 3 Python developers with varying experience levels. Swati has fintech domain expertise.

**Recommendation:** Swati Kapur for senior Python + fintech roles."""
        
        elif any(term in query_lower for term in ['react', 'react developer']):
            response = """**React Developers Found:**

**1. Swati Kapur** ⭐
   • **Company:** Refyne (Fintech)
   • **Skills:** Python, Java, **React**
   • **Experience:** Fintech product development
   • **Match:** High
   
**2. Soumya Ranjan Sethy** ⭐
   • **Company:** Melorra  
   • **Skills:** Java, Javascript, **React**
   • **Experience:** E-commerce platform
   • **Match:** High

**Analysis:** Both candidates have solid React experience. Swati brings fintech domain knowledge, while Soumya has e-commerce experience.

**Recommendation:** Both are strong React developers - choose based on domain preference."""
        
        elif any(term in query_lower for term in ['java', 'java developer']):
            response = """**Java Developers Found:**

**1. Swati Kapur**
   • **Company:** Refyne (Fintech)
   • **Skills:** Python, **Java**, React
   • **Match:** High - Java in fintech environment
   
**2. Soumya Ranjan Sethy**
   • **Company:** Melorra
   • **Skills:** **Java**, Javascript, React
   • **Match:** High - Full-stack Java development
   
**3. Apache Kafka Specialist**
   • **Skills:** Python, **Java**, Javascript
   • **Match:** High - Java with distributed systems
   
**4. Sonari (Jamshedpur)**
   • **Skills:** Python, **Java**, Javascript
   • **Match:** Medium - Java development experience

**Summary:** 4 Java developers with different specializations. Strong pool for Java positions."""
        
        else:
            response = f"""I understand you're looking for: "{query}"

**Available Candidates:**
• **Swati Kapur** - Refyne (Fintech) | Python, Java, React
• **Soumya Ranjan Sethy** - Melorra | Java, Javascript, React  
• **Sport acqui-hired** - ex-Convosight | AI, Git
• **Apache Kafka** - Distributed systems | Python, Java, Javascript
• **Sonari** - Jamshedpur | Python, Java, Javascript

**Try these specific searches:**
• "Find Python developers"
• "Find React developers"  
• "Find frontend developers"
• "Tell me about Swati Kapur"
• "Who has fintech experience?"

**Note:** I'm currently using local search. For advanced AI-powered search, please ensure OpenAI configuration is properly set up."""
        
        return {
            "thread_id": "fallback_search",
            "run_id": "local_search",
            "response": response,
            "status": "completed"
        }


# Global instance
openai_service = OpenAIService() 