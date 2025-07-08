import os
import tempfile
from typing import Dict, List, Optional, Any
import re
import json
import logging
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class SimpleResumeParser:
    def __init__(self):
        pass
    
    def parse_resume(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """Parse resume and extract structured data"""
        try:
            logger.info(f"🔍 Starting resume parsing for file: {file_path} (type: {file_type})")
            
            # Extract text based on file type
            if file_type.lower() == "pdf":
                logger.info(f"📄 Processing PDF file...")
                text = self._extract_text_from_pdf(file_path)
            elif file_type.lower() == "docx":
                logger.info(f"📄 Processing DOCX file...")
                text = self._extract_text_from_docx(file_path)
            elif file_type.lower() == "txt":
                logger.info(f"📄 Processing TXT file...")
                text = self._extract_text_from_txt(file_path)
            else:
                logger.error(f"❌ Unsupported file type: {file_type}")
                return {"success": False, "error": f"Unsupported file type: {file_type}"}
            
            logger.info(f"✅ Text extraction completed. Length: {len(text)} characters")
            
            # Parse the extracted text
            logger.info(f"🔍 Starting text analysis and parsing...")
            parsed_data = self._extract_structured_data(text)
            
            logger.info(f"✅ Text parsing completed")
            logger.info(f"📝 Found name: {parsed_data.get('name', 'Not found')}")
            logger.info(f"📧 Found email: {parsed_data.get('email', 'Not found')}")
            logger.info(f"📱 Found phone: {parsed_data.get('phone', 'Not found')}")
            logger.info(f"🛠️ Found skills: {len(parsed_data.get('skills', []))}")
            logger.info(f"⚙️ Found technologies: {len(parsed_data.get('technologies', []))}")
            logger.info(f"💼 Found experience entries: {len(parsed_data.get('experience', []))}")
            logger.info(f"🎓 Found education entries: {len(parsed_data.get('education', []))}")
            
            return {
                "success": True,
                "parsed_data": parsed_data,
                "raw_text": text,
                "chunks": self._create_chunks(text)
            }
            
        except Exception as e:
            logger.error(f"❌ Error parsing resume: {e}")
            return {"success": False, "error": str(e)}
    
    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF using pdfminer as fallback"""
        try:
            from pdfminer.high_level import extract_text
            return extract_text(file_path)
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return ""
    
    def _extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX using python-docx"""
        try:
            import docx
            doc = docx.Document(file_path)
            text = []
            for paragraph in doc.paragraphs:
                text.append(paragraph.text)
            return "\n".join(text)
        except Exception as e:
            logger.warning(f"python-docx not available, treating as text: {e}")
            return self._extract_text_from_txt(file_path)
    
    def _extract_text_from_txt(self, file_path: str) -> str:
        """Extract text from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
    
    def _extract_structured_data(self, text: str) -> Dict[str, Any]:
        """Extract structured data from resume text using regex patterns"""
        
        # Extract basic information
        name = self._extract_name(text)
        email = self._extract_email(text)
        phone = self._extract_phone(text)
        
        # Extract professional information
        skills = self._extract_skills(text)
        experience = self._extract_experience(text)
        education = self._extract_education(text)
        
        # Extract current role and company
        current_role, current_company = self._extract_current_position(text)
        
        # Calculate years of experience
        years_experience = self._calculate_years_experience(experience)
        
        # Determine domain
        domain = self._classify_domain(text, skills)
        
        return {
            "name": name,
            "email": email,
            "phone": phone,
            "current_role": current_role,
            "current_company": current_company,
            "years_experience": years_experience,
            "domain": domain,
            "skills": skills,
            "technologies": self._extract_technologies(text),
            "experience": experience,
            "education": education
        }
    
    def _extract_name(self, text: str) -> Optional[str]:
        """Extract candidate name using simple patterns"""
        lines = text.split('\n')
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if line and len(line.split()) <= 4 and len(line) > 2:  # Likely a name
                # Check if it doesn't contain common non-name words
                non_name_words = ['resume', 'cv', 'experience', 'skills', 'education', 'phone', 'email', '@']
                if not any(word.lower() in line.lower() for word in non_name_words):
                    # Check if it looks like a name (contains letters)
                    if re.search(r'[a-zA-Z]', line):
                        return line
        
        return None
    
    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email address"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(email_pattern, text)
        return match.group() if match else None
    
    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number"""
        # More flexible phone pattern
        phone_patterns = [
            r'(\+?1?[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
            r'(\+91[-.\s]?)?[6-9]\d{9}',  # Indian phone numbers
            r'(\+\d{1,3}[-.\s]?)?\d{10,}',  # International numbers
        ]
        
        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                return ''.join(match.groups() if match.groups() else [match.group()])
        return None
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills from text"""
        # Common skills to look for
        common_skills = [
            'python', 'java', 'javascript', 'react', 'node.js', 'sql', 'aws',
            'docker', 'kubernetes', 'machine learning', 'ai', 'data science',
            'project management', 'agile', 'scrum', 'git', 'devops',
            'html', 'css', 'typescript', 'angular', 'vue', 'mongodb',
            'postgresql', 'mysql', 'redis', 'elasticsearch', 'kafka',
            'spring', 'django', 'flask', 'express', 'fastapi', 'rest api',
            'microservices', 'cloud computing', 'azure', 'gcp', 'jenkins',
            'ci/cd', 'terraform', 'ansible', 'linux', 'windows', 'macos'
        ]
        
        found_skills = []
        text_lower = text.lower()
        
        for skill in common_skills:
            if skill.lower() in text_lower:
                found_skills.append(skill.title())
        
        return list(set(found_skills))  # Remove duplicates
    
    def _extract_technologies(self, text: str) -> List[str]:
        """Extract technologies from text"""
        # Technology keywords
        technologies = [
            'python', 'java', 'javascript', 'typescript', 'react', 'angular',
            'vue', 'node.js', 'express', 'django', 'flask', 'spring',
            'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins',
            'git', 'github', 'gitlab', 'jira', 'confluence', 'figma',
            'photoshop', 'illustrator', 'sketch'
        ]
        
        found_tech = []
        text_lower = text.lower()
        
        for tech in technologies:
            if tech.lower() in text_lower:
                found_tech.append(tech.title())
        
        return list(set(found_tech))  # Remove duplicates
    
    def _extract_experience(self, text: str) -> List[Dict[str, Any]]:
        """Extract work experience"""
        # Look for year patterns
        experience_patterns = [
            r'(\d{4})\s*[-–]\s*(\d{4}|present|current)',
            r'(\d{4})\s*[-–]\s*(present|current)',
            r'(\d{1,2}/\d{4})\s*[-–]\s*(\d{1,2}/\d{4}|present|current)'
        ]
        
        experiences = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            for pattern in experience_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    start_period = match.group(1)
                    end_period = match.group(2)
                    
                    # Try to extract role and company from surrounding lines
                    role = ""
                    company = ""
                    
                    # Look at previous and next lines for context
                    if i > 0:
                        prev_line = lines[i-1].strip()
                        if prev_line and len(prev_line) > 3:
                            role = prev_line
                    
                    if i < len(lines) - 1:
                        next_line = lines[i+1].strip()
                        if next_line and len(next_line) > 3:
                            company = next_line
                    
                    # Extract year from start_period
                    start_year = re.search(r'\d{4}', start_period)
                    start_year = start_year.group() if start_year else start_period
                    
                    experiences.append({
                        "role": role,
                        "company": company,
                        "start_year": start_year,
                        "end_year": end_period,
                        "period": f"{start_period} - {end_period}"
                    })
        
        return experiences[:5]  # Return max 5 experiences
    
    def _extract_education(self, text: str) -> List[Dict[str, Any]]:
        """Extract education information"""
        education_keywords = ['education', 'degree', 'university', 'college', 'bachelor', 'master', 'phd', 'b.tech', 'm.tech', 'mba']
        education = []
        
        lines = text.split('\n')
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in education_keywords):
                # Extract degree and institution
                degree = line.strip()
                institution = ""
                
                # Look at next line for institution
                if i < len(lines) - 1:
                    next_line = lines[i+1].strip()
                    if next_line and len(next_line) > 3:
                        institution = next_line
                
                education.append({
                    "degree": degree,
                    "institution": institution
                })
        
        return education[:3]  # Return max 3 education entries
    
    def _extract_current_position(self, text: str) -> tuple:
        """Extract current role and company"""
        # Look for recent experience entries
        experiences = self._extract_experience(text)
        if experiences:
            latest = experiences[0]  # Assuming first is most recent
            return latest.get("role", ""), latest.get("company", "")
        
        # Fallback: look for common patterns
        current_patterns = [
            r'current(?:ly)?\s+(?:working\s+)?(?:as\s+)?(.+?)(?:at|@)\s+(.+)',
            r'(?:working\s+)?(?:as\s+)?(.+?)\s+(?:at|@)\s+(.+)',
        ]
        
        for pattern in current_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                role = match.group(1).strip()
                company = match.group(2).strip()
                return role, company
        
        return "", ""
    
    def _calculate_years_experience(self, experience: List[Dict[str, Any]]) -> float:
        """Calculate total years of experience"""
        total_years = 0
        current_year = 2024  # You might want to make this dynamic
        
        for exp in experience:
            start_year_str = exp.get("start_year", "")
            end_year_str = exp.get("end_year", "")
            
            try:
                start_year = int(re.search(r'\d{4}', str(start_year_str)).group()) if re.search(r'\d{4}', str(start_year_str)) else 0
                
                if str(end_year_str).lower() in ["present", "current"]:
                    end_year = current_year
                else:
                    end_year_match = re.search(r'\d{4}', str(end_year_str))
                    end_year = int(end_year_match.group()) if end_year_match else current_year
                
                if start_year > 0:
                    total_years += max(0, end_year - start_year)
            except (ValueError, AttributeError):
                continue
        
        return float(total_years)
    
    def _classify_domain(self, text: str, skills: List[str]) -> str:
        """Classify the domain based on skills and text content"""
        text_lower = text.lower()
        
        # Domain classification based on keywords
        if any(word in text_lower for word in ['frontend', 'ui', 'ux', 'react', 'angular', 'vue', 'html', 'css']):
            return 'frontend'
        elif any(word in text_lower for word in ['backend', 'api', 'server', 'database', 'sql', 'nosql']):
            return 'backend'
        elif any(word in text_lower for word in ['fullstack', 'full-stack', 'full stack']):
            return 'fullstack'
        elif any(word in text_lower for word in ['data science', 'machine learning', 'ai', 'ml', 'analytics']):
            return 'data_science'
        elif any(word in text_lower for word in ['devops', 'cloud', 'aws', 'azure', 'docker', 'kubernetes']):
            return 'devops'
        elif any(word in text_lower for word in ['mobile', 'ios', 'android', 'react native', 'flutter']):
            return 'mobile'
        elif any(word in text_lower for word in ['qa', 'testing', 'quality assurance', 'test automation']):
            return 'qa'
        elif any(word in text_lower for word in ['product', 'project management', 'agile', 'scrum']):
            return 'product'
        else:
            return 'general'
    
    def _create_chunks(self, text: str) -> List[str]:
        """Create text chunks for processing"""
        logger.info(f"✂️ Creating chunks from resume text (length: {len(text)} chars)")
        
        # Simple chunking by paragraphs
        paragraphs = text.split('\n\n')
        chunks = []
        
        for paragraph in paragraphs:
            if paragraph.strip():
                chunks.append(paragraph.strip())
        
        logger.info(f"✅ Created {len(chunks)} chunks from resume")
        return chunks


# Create a singleton instance
simple_resume_parser = SimpleResumeParser() 