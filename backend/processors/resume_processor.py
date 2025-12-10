"""
Resume/CV Processor for extracting structured information.

Extracts structured fields from resumes and CVs using LLM-based extraction
with regex fallback:
- Personal information (name, contact, location)
- Education history (schools, degrees, majors)
- Work experience (companies, positions, dates)
- Skills and certifications
- Languages and proficiencies

Ported from RAGFlow's rag/app/resume.py with LLM enhancement.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.config import settings
from backend.processors.base import DomainProcessor, ProcessorResult
from backend.processors.llm_resume_extractor import LLMResumeExtractor

logger = logging.getLogger(__name__)


# Detection keywords for resume identification
RESUME_KEYWORDS = {
    "resume", "cv", "curriculum vitae", "work experience",
    "education", "skills", "professional experience",
    "employment history", "qualifications", "objective",
    "career summary", "professional summary", "core competencies",
}

# Section headers for parsing
SECTION_PATTERNS = {
    "personal": r"(?i)^(personal\s*info|contact|about\s*me)",
    "education": r"(?i)^(education|academic|qualifications|degrees?)",
    "experience": r"(?i)^(experience|employment|work\s*history|professional\s*experience|career)",
    "skills": r"(?i)^(skills|technical\s*skills|core\s*competencies|expertise|technologies)",
    "certifications": r"(?i)^(certifications?|licenses?|credentials|accreditations)",
    "languages": r"(?i)^(languages?|language\s*proficiency)",
    "projects": r"(?i)^(projects?|personal\s*projects|portfolio)",
    "publications": r"(?i)^(publications?|papers?|research)",
    "awards": r"(?i)^(awards?|honors?|achievements?|recognition)",
    "references": r"(?i)^(references?|recommendations?)",
    "summary": r"(?i)^(summary|objective|profile|career\s*summary|professional\s*summary)",
}


class ResumeProcessor(DomainProcessor):
    """
    Processor for resume and CV documents.

    Extracts structured information including:
    - Personal details (name, email, phone, location)
    - Education history with degrees and dates
    - Work experience with companies and roles
    - Skills categorized by type
    - Certifications and languages
    """

    name = "resume"
    supported_content_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    ]

    # Regex patterns for field extraction
    EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
    PHONE_PATTERN = re.compile(
        r"(?:\+\d{1,3}[-.\s]?)?"
        r"(?:\(?\d{1,4}\)?[-.\s]?)?"
        r"\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}"
    )
    URL_PATTERN = re.compile(
        r"(?:https?://)?(?:www\.)?(?:linkedin\.com|github\.com)[\w./-]*"
    )
    DATE_PATTERN = re.compile(
        r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*)?"
        r"(?:19|20)\d{2}"
        r"(?:\s*[-–]\s*(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*)?(?:(?:19|20)\d{2}|Present|Current))?"
    )
    DEGREE_PATTERNS = [
        r"(?i)\b(Ph\.?D\.?|Doctorate|Doctor\s+of)\b",
        r"(?i)\b(M\.?S\.?|M\.?A\.?|Master(?:'s)?(?:\s+of)?)\b",
        r"(?i)\b(B\.?S\.?|B\.?A\.?|Bachelor(?:'s)?(?:\s+of)?)\b",
        r"(?i)\b(MBA|M\.?B\.?A\.?)\b",
        r"(?i)\b(Associate(?:'s)?(?:\s+Degree)?)\b",
        r"(?i)\b(High\s+School|Secondary|GED)\b",
    ]

    async def process(
        self,
        content: str,
        metadata: Dict[str, Any],
        filename: str,
    ) -> ProcessorResult:
        """
        Process resume content and extract structured information.

        Uses LLM-based extraction as primary method (if enabled),
        with regex-based extraction as fallback.

        Args:
            content: Resume text content
            metadata: User-provided metadata
            filename: Original filename

        Returns:
            ProcessorResult with extracted resume data
        """
        logger.info(f"Processing resume: {filename}")

        # Try LLM-based extraction first (if enabled)
        llm_extracted = None
        use_llm = settings.DOMAIN_PROCESSORS_ENABLED and settings.DOMAIN_DETECTION_USE_LLM

        if use_llm:
            try:
                logger.info("Using LLM-based resume extraction")
                llm_extracted = await LLMResumeExtractor.extract(content)

                # Check if extraction was successful
                if llm_extracted.get("integrity_score", 0) >= 0.3:
                    return self._build_result_from_llm(content, llm_extracted)
                else:
                    logger.warning(
                        "LLM extraction low quality (%.2f), falling back to regex",
                        llm_extracted.get("integrity_score", 0)
                    )
            except Exception as e:
                logger.warning("LLM extraction failed, falling back to regex: %s", e)

        # Fallback to regex-based extraction
        logger.info("Using regex-based resume extraction")
        return await self._process_with_regex(content, filename)

    def _build_result_from_llm(
        self,
        content: str,
        llm_extracted: Dict[str, Any],
    ) -> ProcessorResult:
        """Build ProcessorResult from LLM extraction.

        Args:
            content: Original resume content
            llm_extracted: LLM-extracted data

        Returns:
            ProcessorResult with extracted resume data
        """
        personal = llm_extracted.get("personal", {})
        career = llm_extracted.get("career", {})
        education = llm_extracted.get("education", [])
        experience = llm_extracted.get("experience", [])
        skills = llm_extracted.get("skills", {})
        derived = llm_extracted.get("derived", {})

        # Build personal_info matching existing format
        personal_info = {
            "name": personal.get("name"),
            "email": personal.get("email"),
            "phone": personal.get("phone"),
            "location": personal.get("location"),
            "links": personal.get("links", []),
            # RAGFlow-style fields
            "gender": personal.get("gender"),
            "age": personal.get("age"),
            "birth_date": personal.get("birth_date"),
            "name_pinyin": personal.get("name_pinyin"),
            "nationality": personal.get("nationality"),
        }
        # Remove None values
        personal_info = {k: v for k, v in personal_info.items() if v is not None}

        # Build career info (RAGFlow-style)
        career_info = {
            "current_position": career.get("current_position"),
            "current_company": career.get("current_company"),
            "industry": career.get("industry"),
            "work_experience_years": career.get("work_experience_years"),
            "management_experience": career.get("management_experience"),
            "expected_position": career.get("expected_position"),
            "expected_city": career.get("expected_city"),
            "expected_salary_min": career.get("expected_salary_min"),
            "expected_salary_max": career.get("expected_salary_max"),
            "current_salary": career.get("current_salary"),
        }
        career_info = {k: v for k, v in career_info.items() if v is not None}

        # Build document metadata
        document_metadata = {
            "document_type": "resume",
            "extraction_method": "llm",
            "personal_info": personal_info,
            "career_info": career_info,
            "education": education,
            "experience": experience,
            "skills": skills.get("technical", []) + skills.get("soft", []),
            "certifications": skills.get("certifications", []),
            "languages": skills.get("languages", []),
            "projects": llm_extracted.get("projects", []),
            "additional": llm_extracted.get("additional", {}),
            # RAGFlow-style derived fields
            "derived": derived,
            "tags": llm_extracted.get("tags", []),
            "integrity_score": llm_extracted.get("integrity_score", 0.0),
            # RAGFlow-compatible field mapping
            "ragflow_fields": LLMResumeExtractor.to_ragflow_format(llm_extracted),
        }

        # Create chunk annotations
        chunk_annotations = []

        for edu in education:
            chunk_annotations.append({
                "type": "education",
                "institution": edu.get("institution"),
                "degree": edu.get("degree"),
                "preserve_boundary": True,
            })

        for exp in experience:
            chunk_annotations.append({
                "type": "experience",
                "company": exp.get("company"),
                "position": exp.get("position"),
                "preserve_boundary": True,
            })

        confidence = min(0.98, 0.6 + llm_extracted.get("integrity_score", 0) * 0.4)

        logger.info(
            "LLM resume extraction complete: %d edu, %d exp, %.0f%% integrity",
            len(education),
            len(experience),
            llm_extracted.get("integrity_score", 0) * 100,
        )

        return ProcessorResult(
            content=content,
            document_metadata=document_metadata,
            chunk_annotations=chunk_annotations,
            processor_name=self.name,
            confidence=confidence,
        )

    async def _process_with_regex(
        self,
        content: str,
        filename: str,
    ) -> ProcessorResult:
        """Process resume using regex-based extraction (fallback).

        Args:
            content: Resume text content
            filename: Original filename

        Returns:
            ProcessorResult with extracted resume data
        """
        # Extract all fields using regex
        personal_info = self._extract_personal_info(content)
        education = self._extract_education(content)
        experience = self._extract_experience(content)
        skills = self._extract_skills(content)
        certifications = self._extract_certifications(content)
        languages = self._extract_languages(content)

        # Build document metadata
        document_metadata = {
            "document_type": "resume",
            "extraction_method": "regex",
            "personal_info": personal_info,
            "education": education,
            "experience": experience,
            "skills": skills,
            "certifications": certifications,
            "languages": languages,
            "sections_found": self._identify_sections(content),
        }

        # Create chunk annotations for key sections
        chunk_annotations = []

        # Annotate education section
        for edu in education:
            chunk_annotations.append({
                "type": "education",
                "institution": edu.get("institution"),
                "degree": edu.get("degree"),
                "preserve_boundary": True,
            })

        # Annotate experience section
        for exp in experience:
            chunk_annotations.append({
                "type": "experience",
                "company": exp.get("company"),
                "position": exp.get("position"),
                "preserve_boundary": True,
            })

        # Calculate confidence based on extraction quality
        fields_found = sum([
            1 if personal_info.get("name") else 0,
            1 if personal_info.get("email") else 0,
            1 if education else 0,
            1 if experience else 0,
            1 if skills else 0,
        ])
        confidence = min(0.95, 0.5 + (fields_found * 0.1))

        logger.info(
            "Regex resume extraction complete: %d edu, %d exp, %d skills",
            len(education),
            len(experience),
            len(skills),
        )

        return ProcessorResult(
            content=content,
            document_metadata=document_metadata,
            chunk_annotations=chunk_annotations,
            processor_name=self.name,
            confidence=confidence,
        )

    def can_process(self, content: str, metadata: Dict[str, Any]) -> float:
        """
        Determine if content is a resume/CV.

        Args:
            content: Document text
            metadata: User metadata

        Returns:
            Confidence score (0-1)
        """
        content_lower = content.lower()

        # Check for resume keywords
        keyword_matches = sum(
            1 for kw in RESUME_KEYWORDS if kw in content_lower
        )

        # Check for typical resume sections
        section_matches = sum(
            1 for pattern in SECTION_PATTERNS.values()
            if re.search(pattern, content, re.MULTILINE)
        )

        # Check for contact info patterns
        has_email = bool(self.EMAIL_PATTERN.search(content))
        has_phone = bool(self.PHONE_PATTERN.search(content))

        # Calculate confidence
        score = 0.0
        score += min(0.3, keyword_matches * 0.05)
        score += min(0.3, section_matches * 0.05)
        score += 0.1 if has_email else 0
        score += 0.1 if has_phone else 0

        # Boost for explicit resume indicators
        if "curriculum vitae" in content_lower or "resume" in content_lower:
            score += 0.2

        return min(1.0, score)

    def _extract_personal_info(self, content: str) -> Dict[str, Any]:
        """Extract personal information from resume."""
        info: Dict[str, Any] = {}

        # Extract email
        email_match = self.EMAIL_PATTERN.search(content)
        if email_match:
            info["email"] = email_match.group()

        # Extract phone
        phone_match = self.PHONE_PATTERN.search(content)
        if phone_match:
            phone = phone_match.group().strip()
            # Clean up phone number
            if len(re.sub(r"\D", "", phone)) >= 7:
                info["phone"] = phone

        # Extract LinkedIn/GitHub URLs
        urls = self.URL_PATTERN.findall(content)
        if urls:
            info["links"] = urls[:3]

        # Extract name (usually first line or after "Name:")
        name = self._extract_name(content)
        if name:
            info["name"] = name

        # Extract location
        location = self._extract_location(content)
        if location:
            info["location"] = location

        return info

    def _extract_name(self, content: str) -> Optional[str]:
        """Extract candidate name from resume."""
        lines = content.strip().split("\n")

        # Try explicit name field
        for line in lines[:10]:
            if re.match(r"(?i)^name\s*[:\-]?\s*", line):
                name = re.sub(r"(?i)^name\s*[:\-]?\s*", "", line).strip()
                if name and len(name) < 50:
                    return name

        # First non-empty line is often the name
        for line in lines[:5]:
            line = line.strip()
            # Skip if it looks like a header, contact info, or is too long
            if not line or len(line) > 50:
                continue
            if self.EMAIL_PATTERN.search(line):
                continue
            if self.PHONE_PATTERN.search(line):
                continue
            if any(kw in line.lower() for kw in ["resume", "cv", "curriculum"]):
                continue
            if re.match(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}$", line):
                return line

        return None

    def _extract_location(self, content: str) -> Optional[str]:
        """Extract location from resume."""
        # Common location patterns
        location_patterns = [
            r"(?i)(?:location|address|based\s+in)[:\s]+([^\n]+)",
            r"(?i)([A-Z][a-z]+(?:,\s*[A-Z]{2})?(?:,\s*\d{5})?)",
        ]

        for pattern in location_patterns:
            match = re.search(pattern, content[:1500])
            if match:
                loc = match.group(1).strip()
                if 3 < len(loc) < 100:
                    return loc

        return None

    def _extract_education(self, content: str) -> List[Dict[str, Any]]:
        """Extract education history from resume."""
        education = []
        edu_section = self._extract_section(content, "education")

        if not edu_section:
            return education

        # Split by common delimiters
        entries = re.split(r"\n{2,}|\n(?=[A-Z])", edu_section)

        for entry in entries:
            if not entry.strip():
                continue

            edu_entry: Dict[str, Any] = {}

            # Extract degree
            for pattern in self.DEGREE_PATTERNS:
                match = re.search(pattern, entry)
                if match:
                    edu_entry["degree"] = match.group().strip()
                    break

            # Extract dates
            date_match = self.DATE_PATTERN.search(entry)
            if date_match:
                edu_entry["dates"] = date_match.group().strip()

            # Extract institution (usually first line or after degree)
            lines = entry.strip().split("\n")
            for line in lines[:3]:
                line = line.strip()
                if line and not self.DATE_PATTERN.match(line):
                    if "degree" not in edu_entry or line != edu_entry.get("degree"):
                        edu_entry["institution"] = line[:100]
                        break

            # Extract major/field of study
            major_match = re.search(
                r"(?i)(?:major|field|specialization|concentration)[:\s]+([^\n,]+)",
                entry
            )
            if major_match:
                edu_entry["major"] = major_match.group(1).strip()

            if edu_entry:
                education.append(edu_entry)

        return education[:5]  # Limit to 5 entries

    def _extract_experience(self, content: str) -> List[Dict[str, Any]]:
        """Extract work experience from resume."""
        experience = []
        exp_section = self._extract_section(content, "experience")

        if not exp_section:
            return experience

        # Split by double newlines or lines starting with company names
        entries = re.split(r"\n{2,}", exp_section)

        for entry in entries:
            if not entry.strip() or len(entry) < 20:
                continue

            exp_entry: Dict[str, Any] = {}

            # Extract dates
            date_match = self.DATE_PATTERN.search(entry)
            if date_match:
                exp_entry["dates"] = date_match.group().strip()

            # Extract lines for company/position
            lines = entry.strip().split("\n")

            # First line is usually company or position
            if lines:
                first_line = lines[0].strip()
                if not self.DATE_PATTERN.match(first_line):
                    # Detect if it's a position or company
                    position_keywords = ["engineer", "manager", "developer", "analyst",
                                         "director", "specialist", "lead", "senior"]
                    if any(kw in first_line.lower() for kw in position_keywords):
                        exp_entry["position"] = first_line[:100]
                    else:
                        exp_entry["company"] = first_line[:100]

            # Second line is the other one
            if len(lines) > 1:
                second_line = lines[1].strip()
                if not self.DATE_PATTERN.match(second_line):
                    if "position" not in exp_entry:
                        exp_entry["position"] = second_line[:100]
                    elif "company" not in exp_entry:
                        exp_entry["company"] = second_line[:100]

            # Extract description
            desc_lines = [l.strip() for l in lines[2:] if l.strip()]
            if desc_lines:
                exp_entry["description"] = " ".join(desc_lines)[:500]

            if exp_entry and ("company" in exp_entry or "position" in exp_entry):
                experience.append(exp_entry)

        return experience[:10]  # Limit to 10 entries

    def _extract_skills(self, content: str) -> List[str]:
        """Extract skills from resume."""
        skills = set()

        # Try to find skills section
        skills_section = self._extract_section(content, "skills")

        if skills_section:
            # Extract skills from section
            # Split by common delimiters
            skill_items = re.split(r"[,\n|/]|(?:\s{2,})", skills_section)
            for item in skill_items:
                item = item.strip().strip("-*")
                if item and 2 < len(item) < 50:
                    # Skip if it's a header or level indicator
                    if not re.match(r"(?i)^(beginner|intermediate|advanced|expert|proficient)", item):
                        skills.add(item)

        return list(skills)[:30]  # Limit to 30 skills

    def _extract_certifications(self, content: str) -> List[str]:
        """Extract certifications from resume."""
        certs = []
        cert_section = self._extract_section(content, "certifications")

        if not cert_section:
            return certs

        lines = cert_section.split("\n")
        for line in lines:
            line = line.strip().strip("-*")
            if line and 5 < len(line) < 100:
                certs.append(line)

        return certs[:10]

    def _extract_languages(self, content: str) -> List[Dict[str, str]]:
        """Extract languages and proficiency levels."""
        languages = []
        lang_section = self._extract_section(content, "languages")

        if not lang_section:
            return languages

        lines = lang_section.split("\n")
        for line in lines:
            line = line.strip().strip("-*")
            if not line:
                continue

            # Try to extract language and level
            level_match = re.search(
                r"(?i)(native|fluent|advanced|intermediate|basic|beginner|proficient)",
                line
            )
            if level_match:
                language = line[:level_match.start()].strip().strip(":-")
                level = level_match.group().title()
                if language:
                    languages.append({"language": language, "level": level})
            else:
                languages.append({"language": line, "level": "Not specified"})

        return languages[:10]

    def _extract_section(self, content: str, section_name: str) -> Optional[str]:
        """Extract a specific section from resume content."""
        pattern = SECTION_PATTERNS.get(section_name)
        if not pattern:
            return None

        lines = content.split("\n")

        # Find section start
        start_idx = None
        for i, line in enumerate(lines):
            if re.match(pattern, line.strip()):
                start_idx = i + 1
                break

        if start_idx is None:
            return None

        # Find section end (next section header)
        end_idx = len(lines)
        for name, pat in SECTION_PATTERNS.items():
            if name == section_name:
                continue
            for i in range(start_idx, len(lines)):
                if re.match(pat, lines[i].strip()):
                    end_idx = min(end_idx, i)
                    break

        return "\n".join(lines[start_idx:end_idx]).strip()

    def _identify_sections(self, content: str) -> List[str]:
        """Identify which sections are present in the resume."""
        sections = []
        for name, pattern in SECTION_PATTERNS.items():
            if re.search(pattern, content, re.MULTILINE):
                sections.append(name)
        return sections
