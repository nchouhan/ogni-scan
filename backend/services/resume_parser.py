import os
import tempfile
from typing import Dict, List, Optional, Any
from unstructured.partition.auto import partition
from pdfminer.high_level import extract_text
import spacy
import re
import json
import logging
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class ResumeParser:
    def __init__(self):
        # Load spaCy model for NER
        self.nlp = None
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model not found. Installing...")
            try:
                os.system("python -m spacy download en_core_web_sm")
                self.nlp = spacy.load("en_core_web_sm")
            except Exception as e:
                logger.error(f"Failed to install spaCy model: {e}")
                logger.warning("Continuing without spaCy model. NER features will be limited.")
    
    def parse_resume(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """Parse resume and extract structured data"""
        try:
            # Extract text based on file type
            if file_type.lower() == "pdf":
                text = self._extract_text_from_pdf(file_path)
            elif file_type.lower() == "docx":
                text = self._extract_text_from_docx(file_path)
            elif file_type.lower() == "txt":
                text = self._extract_text_from_txt(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            # Extract structured data
            parsed_data = self._extract_structured_data(text)
            
            return {
                "raw_text": text,
                "parsed_data": parsed_data,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error parsing resume {file_path}: {e}")
            return {
                "raw_text": "",
                "parsed_data": {},
                "success": False,
                "error": str(e)
            }
    
    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF using Unstructured.io with fallback to pdfminer"""
        try:
            # Try Unstructured.io first
            elements = partition(filename=file_path)
            text = "\n".join([str(element) for element in elements])
            return text
        except Exception as e:
            logger.warning(f"Unstructured.io failed, using pdfminer fallback: {e}")
            # Fallback to pdfminer
            return extract_text(file_path)
    
    def _extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX using Unstructured.io"""
        elements = partition(filename=file_path)
        return "\n".join([str(element) for element in elements])
    
    def _extract_text_from_txt(self, file_path: str) -> str:
        """Extract text from TXT file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _extract_structured_data(self, text: str) -> Dict[str, Any]:
        """Extract structured data from resume text"""
        doc = self.nlp(text) if self.nlp is not None else None
        
        # Extract basic information
        name = self._extract_name(doc, text)
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
    
    def _extract_name(self, doc, text: str) -> Optional[str]:
        """Extract candidate name using NER"""
        # Use spaCy NER if available
        if self.nlp is not None:
            # Look for PERSON entities
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    return ent.text.strip()
        
        # Fallback: look for common name patterns
        lines = text.split('\n')
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if line and len(line.split()) <= 4:  # Likely a name
                # Check if it doesn't contain common non-name words
                non_name_words = ['resume', 'cv', 'experience', 'skills', 'education']
                if not any(word.lower() in line.lower() for word in non_name_words):
                    return line
        
        return None
    
    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email address"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(email_pattern, text)
        return match.group() if match else None
    
    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number"""
        phone_pattern = r'(\+?1?[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
        match = re.search(phone_pattern, text)
        if match:
            return ''.join(match.groups())
        return None
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills from text"""
        # Common skills to look for
        common_skills = [
            'python', 'java', 'javascript', 'react', 'node.js', 'sql', 'aws',
            'docker', 'kubernetes', 'machine learning', 'ai', 'data science',
            'project management', 'agile', 'scrum', 'git', 'devops',
            'html', 'css', 'typescript', 'angular', 'vue', 'mongodb',
            'postgresql', 'mysql', 'redis', 'elasticsearch', 'kafka'
        ]
        
        found_skills = []
        text_lower = text.lower()
        
        for skill in common_skills:
            if skill in text_lower:
                found_skills.append(skill.title())
        
        return found_skills
    
    def _extract_technologies(self, text: str) -> List[str]:
        """Extract technologies from text"""
        # Technology keywords
        technologies = [
            'python', 'java', 'javascript', 'typescript', 'react', 'angular',
            'vue', 'node.js', 'express', 'django', 'flask', 'spring',
            'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins',
            'git', 'github', 'gitlab', 'jira', 'confluence'
        ]
        
        found_tech = []
        text_lower = text.lower()
        
        for tech in technologies:
            if tech in text_lower:
                found_tech.append(tech.title())
        
        return found_tech
    
    def _extract_experience(self, text: str) -> List[Dict[str, Any]]:
        """Extract work experience"""
        # Simple regex-based extraction
        experience_pattern = r'(\d{4})\s*[-–]\s*(\d{4}|present|current)'
        experiences = []
        
        lines = text.split('\n')
        for i, line in enumerate(lines):
            match = re.search(experience_pattern, line, re.IGNORECASE)
            if match:
                start_year = match.group(1)
                end_year = match.group(2)
                
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
                
                experiences.append({
                    "role": role,
                    "company": company,
                    "start_year": start_year,
                    "end_year": end_year
                })
        
        return experiences
    
    def _extract_education(self, text: str) -> List[Dict[str, Any]]:
        """Extract education information"""
        education_keywords = ['education', 'degree', 'university', 'college', 'bachelor', 'master', 'phd']
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
        
        return education
    
    def _extract_current_position(self, text: str) -> tuple:
        """Extract current role and company"""
        # Look for recent experience entries
        experiences = self._extract_experience(text)
        if experiences:
            latest = experiences[0]  # Assuming first is most recent
            return latest.get("role", ""), latest.get("company", "")
        
        return "", ""
    
    def _calculate_years_experience(self, experience: List[Dict[str, Any]]) -> float:
        """Calculate total years of experience"""
        total_years = 0
        current_year = 2024  # You might want to make this dynamic
        
        for exp in experience:
            start_year = int(exp.get("start_year", 0))
            end_year = exp.get("end_year", "")
            
            if end_year.lower() in ["present", "current"]:
                end_year = current_year
            else:
                end_year = int(end_year) if end_year else current_year
            
            total_years += (end_year - start_year)
        
        return float(total_years)
    
    def _classify_domain(self, text: str, skills: List[str]) -> str:
        """Classify the domain based on skills and text content"""
        text_lower = text.lower()
        
        # Domain keywords
        domains = {
            "fintech": ["finance", "banking", "fintech", "payment", "blockchain", "cryptocurrency"],
            "saas": ["saas", "software", "product", "startup", "b2b", "enterprise"],
            "ecommerce": ["ecommerce", "retail", "shopping", "marketplace", "inventory"],
            "healthcare": ["healthcare", "medical", "pharma", "hospital", "patient"],
            "ai_ml": ["machine learning", "ai", "artificial intelligence", "data science", "nlp"],
            "devops": ["devops", "infrastructure", "cloud", "deployment", "ci/cd"]
        }
        
        for domain, keywords in domains.items():
            if any(keyword in text_lower for keyword in keywords):
                return domain
        
        return "general"


# Global instance
resume_parser = ResumeParser() 