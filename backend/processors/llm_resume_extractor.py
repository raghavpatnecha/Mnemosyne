"""
LLM-based resume field extraction.

Uses a language model to extract structured fields from resumes,
matching RAGFlow's field schema for consistency.

Ported from RAGFlow's resume parsing pipeline, adapted for LLM extraction.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import litellm

from backend.config import settings

# Configure litellm to automatically drop unsupported parameters
litellm.drop_params = True

logger = logging.getLogger(__name__)


def _get_model_string() -> str:
    """Get model string following codebase pattern."""
    if settings.LLM_MODEL_STRING:
        return settings.LLM_MODEL_STRING
    return f"{settings.LLM_PROVIDER}/{settings.CHAT_MODEL}"


def _get_litellm_kwargs(model: Optional[str] = None) -> Dict[str, Any]:
    """Get LiteLLM kwargs following codebase pattern."""
    model_string = model or _get_model_string()

    kwargs = {
        "model": model_string,
        "timeout": settings.LLM_TIMEOUT,
    }

    # Add API key if using OpenAI
    if "openai" in model_string.lower() or model_string.startswith("gpt-") or model_string.startswith("o1"):
        kwargs["api_key"] = settings.OPENAI_API_KEY

    if settings.LLM_API_BASE:
        kwargs["api_base"] = settings.LLM_API_BASE

    return kwargs


# JSON schema for structured extraction - matches RAGFlow field_map
# Note: Double braces {{ }} are escaped for .format() - only {content} is replaced
RESUME_EXTRACTION_PROMPT = """Extract structured information from this resume/CV. Return a JSON object with the following fields.

IMPORTANT: Extract ALL information you can find. Use null for fields not present in the resume.

Required JSON structure:
{{
    "personal": {{
        "name": "Full name",
        "name_pinyin": "Name in pinyin (if Chinese name)",
        "gender": "male/female/null",
        "age": null or integer,
        "birth_date": "YYYY-MM-DD or null",
        "phone": "Phone number",
        "email": "Email address",
        "location": "Current city/location",
        "nationality": "Nationality/citizenship",
        "links": ["LinkedIn URL", "GitHub URL", "Portfolio URL"]
    }},
    "career": {{
        "current_position": "Current job title",
        "current_company": "Current employer",
        "industry": "Industry sector",
        "work_experience_years": null or float,
        "management_experience": true/false/null,
        "expected_position": "Desired job title",
        "expected_city": "Desired work location",
        "expected_salary_min": null or integer (annual),
        "expected_salary_max": null or integer (annual),
        "current_salary": null or integer (annual)
    }},
    "education": [
        {{
            "institution": "School/University name",
            "degree": "PhD/Master/Bachelor/Associate/High School",
            "major": "Field of study",
            "start_date": "YYYY or YYYY-MM",
            "end_date": "YYYY or YYYY-MM or Present",
            "gpa": null or float,
            "honors": ["Dean's List", "Cum Laude", etc],
            "is_first_degree": true/false
        }}
    ],
    "experience": [
        {{
            "company": "Company name",
            "position": "Job title",
            "industry": "Industry sector",
            "start_date": "YYYY-MM",
            "end_date": "YYYY-MM or Present",
            "duration_months": null or integer,
            "responsibilities": "Key responsibilities description",
            "achievements": ["Achievement 1", "Achievement 2"],
            "subordinates_count": null or integer
        }}
    ],
    "skills": {{
        "technical": ["Python", "JavaScript", etc],
        "soft": ["Leadership", "Communication", etc],
        "languages": [
            {{"language": "English", "level": "Native/Fluent/Advanced/Intermediate/Basic"}}
        ],
        "certifications": ["AWS Certified", "PMP", etc]
    }},
    "projects": [
        {{
            "name": "Project name",
            "description": "Brief description",
            "technologies": ["Tech1", "Tech2"],
            "role": "Your role",
            "url": "Project URL if any"
        }}
    ],
    "additional": {{
        "publications": ["Publication 1", "Publication 2"],
        "awards": ["Award 1", "Award 2"],
        "volunteer": ["Volunteer experience"],
        "interests": ["Interest 1", "Interest 2"],
        "summary": "Professional summary/objective if present"
    }}
}}

Resume content to extract from:
---
{content}
---

Return ONLY the JSON object, no markdown formatting or explanation."""


class LLMResumeExtractor:
    """Extracts structured resume data using LLM."""

    # Excerpt length for extraction (balance accuracy vs cost)
    MAX_CONTENT_LENGTH = 8000

    @classmethod
    async def extract(
        cls,
        content: str,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extract structured fields from resume using LLM.

        Args:
            content: Resume text content
            model: LLM model to use (defaults to CHAT_MODEL setting)

        Returns:
            Dictionary with extracted resume fields matching RAGFlow schema
        """
        # Truncate if too long
        if len(content) > cls.MAX_CONTENT_LENGTH:
            content = content[: cls.MAX_CONTENT_LENGTH]
            logger.debug("Resume content truncated to %d chars", cls.MAX_CONTENT_LENGTH)

        # Get LiteLLM kwargs following codebase pattern
        litellm_kwargs = _get_litellm_kwargs(model)
        model_string = litellm_kwargs["model"]

        logger.info("Extracting resume fields using model: %s", model_string)

        try:
            response = await litellm.acompletion(
                **litellm_kwargs,
                messages=[
                    {
                        "role": "user",
                        "content": RESUME_EXTRACTION_PROMPT.format(content=content),
                    }
                ],
                temperature=0,  # Deterministic output
                max_tokens=4000,  # Need more for JSON response
                response_format={"type": "json_object"},
            )

            raw_response = response.choices[0].message.content.strip()

            # Parse JSON response
            extracted = cls._parse_json_response(raw_response)

            # Post-process and enrich fields
            extracted = cls._post_process(extracted, content)

            logger.info(
                "LLM extracted resume fields: %d personal, %d edu, %d exp",
                len(extracted.get("personal", {})),
                len(extracted.get("education", [])),
                len(extracted.get("experience", [])),
            )

            return extracted

        except Exception as e:
            logger.error("LLM resume extraction failed: %s", e)
            return cls._empty_result()

    @classmethod
    def _parse_json_response(cls, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response.

        Args:
            response: Raw LLM response

        Returns:
            Parsed dictionary
        """
        # Clean up response
        response = response.strip()

        # Remove markdown code blocks if present
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse JSON response: %s", e)
            return cls._empty_result()

    @classmethod
    def _post_process(
        cls, extracted: Dict[str, Any], original_content: str
    ) -> Dict[str, Any]:
        """Post-process extracted data to add derived fields.

        Adds RAGFlow-style computed fields like work experience years,
        school rankings, etc.

        Args:
            extracted: LLM-extracted data
            original_content: Original resume text

        Returns:
            Enriched data dictionary
        """
        # Calculate work experience if not provided
        career = extracted.get("career", {})
        if not career.get("work_experience_years"):
            years = cls._calculate_work_years(extracted.get("experience", []))
            if years:
                career["work_experience_years"] = years

        # Determine highest degree
        education = extracted.get("education", [])
        if education:
            highest = cls._get_highest_degree(education)
            if highest:
                extracted.setdefault("derived", {})["highest_degree"] = highest

            # Mark first degree
            first_degree = cls._get_first_degree(education)
            if first_degree:
                extracted.setdefault("derived", {})["first_degree"] = first_degree

        # Add integrity score (how complete is the resume)
        extracted["integrity_score"] = cls._calculate_integrity(extracted)

        # Add tags
        extracted["tags"] = cls._generate_tags(extracted)

        return extracted

    @classmethod
    def _calculate_work_years(cls, experience: List[Dict]) -> Optional[float]:
        """Calculate total years of work experience."""
        if not experience:
            return None

        earliest_start = None
        for exp in experience:
            start = exp.get("start_date")
            if start:
                try:
                    year = int(start.split("-")[0])
                    if earliest_start is None or year < earliest_start:
                        earliest_start = year
                except (ValueError, IndexError):
                    continue

        if earliest_start:
            return round(datetime.now().year - earliest_start, 1)
        return None

    @classmethod
    def _get_highest_degree(cls, education: List[Dict]) -> Optional[str]:
        """Get highest degree from education list."""
        degree_rank = {
            "phd": 8,
            "doctorate": 8,
            "doctor": 8,
            "postdoc": 9,
            "master": 6,
            "mba": 6,
            "bachelor": 5,
            "associate": 4,
            "diploma": 3,
            "high school": 2,
            "secondary": 2,
            "ged": 1,
        }

        highest = None
        highest_rank = 0

        for edu in education:
            degree = (edu.get("degree") or "").lower()
            for key, rank in degree_rank.items():
                if key in degree and rank > highest_rank:
                    highest = edu.get("degree")
                    highest_rank = rank
                    break

        return highest

    @classmethod
    def _get_first_degree(cls, education: List[Dict]) -> Optional[Dict]:
        """Get first/undergraduate degree."""
        first_degree_types = ["bachelor", "associate", "diploma"]

        for edu in education:
            degree = (edu.get("degree") or "").lower()
            if any(d in degree for d in first_degree_types):
                return {
                    "institution": edu.get("institution"),
                    "degree": edu.get("degree"),
                    "major": edu.get("major"),
                }
        return None

    @classmethod
    def _calculate_integrity(cls, extracted: Dict[str, Any]) -> float:
        """Calculate resume completeness score (0-1)."""
        score = 0.0
        total = 0.0

        # Personal info (weight: 30%)
        personal = extracted.get("personal", {})
        personal_fields = ["name", "email", "phone", "location"]
        total += 30
        for field in personal_fields:
            if personal.get(field):
                score += 30 / len(personal_fields)

        # Career info (weight: 20%)
        career = extracted.get("career", {})
        career_fields = ["current_position", "current_company", "work_experience_years"]
        total += 20
        for field in career_fields:
            if career.get(field):
                score += 20 / len(career_fields)

        # Education (weight: 25%)
        total += 25
        education = extracted.get("education", [])
        if education:
            score += 15  # Has education
            if any(e.get("degree") for e in education):
                score += 5
            if any(e.get("major") for e in education):
                score += 5

        # Experience (weight: 25%)
        total += 25
        experience = extracted.get("experience", [])
        if experience:
            score += 15  # Has experience
            if any(e.get("responsibilities") for e in experience):
                score += 5
            if len(experience) >= 2:
                score += 5

        return round(score / total, 2) if total > 0 else 0.0

    @classmethod
    def _generate_tags(cls, extracted: Dict[str, Any]) -> List[str]:
        """Generate smart tags for the resume."""
        tags = []

        # Education tags
        derived = extracted.get("derived", {})
        highest = derived.get("highest_degree", "").lower()
        if "phd" in highest or "doctor" in highest:
            tags.append("PhD")
        elif "master" in highest or "mba" in highest:
            tags.append("Master's Degree")
        elif "bachelor" in highest:
            tags.append("Bachelor's Degree")

        # Experience tags
        career = extracted.get("career", {})
        years = career.get("work_experience_years")
        if years:
            if years >= 10:
                tags.append("Senior (10+ years)")
            elif years >= 5:
                tags.append("Mid-level (5-10 years)")
            elif years >= 2:
                tags.append("Junior (2-5 years)")
            else:
                tags.append("Entry-level")

        if career.get("management_experience"):
            tags.append("Management Experience")

        # Skills tags
        skills = extracted.get("skills", {})
        tech_skills = skills.get("technical", [])
        if len(tech_skills) >= 10:
            tags.append("Diverse Technical Skills")

        certs = skills.get("certifications", [])
        if certs:
            tags.append("Certified Professional")

        languages = skills.get("languages", [])
        if len(languages) >= 2:
            tags.append("Multilingual")

        return tags

    @classmethod
    def _empty_result(cls) -> Dict[str, Any]:
        """Return empty result structure."""
        return {
            "personal": {},
            "career": {},
            "education": [],
            "experience": [],
            "skills": {},
            "projects": [],
            "additional": {},
            "derived": {},
            "tags": [],
            "integrity_score": 0.0,
        }

    @classmethod
    def to_ragflow_format(cls, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """Convert extracted data to RAGFlow field format.

        Maps our extracted fields to RAGFlow's field_map structure
        for compatibility and search optimization.

        Args:
            extracted: LLM-extracted data

        Returns:
            RAGFlow-compatible field dictionary
        """
        personal = extracted.get("personal", {})
        career = extracted.get("career", {})
        education = extracted.get("education", [])
        experience = extracted.get("experience", [])
        skills = extracted.get("skills", {})
        derived = extracted.get("derived", {})

        # Build RAGFlow-compatible fields
        ragflow = {
            # Personal
            "name_kwd": personal.get("name"),
            "name_pinyin_kwd": personal.get("name_pinyin"),
            "gender_kwd": personal.get("gender"),
            "age_int": personal.get("age"),
            "birth_dt": personal.get("birth_date"),
            "phone_kwd": personal.get("phone"),
            "email_tks": personal.get("email"),
            # Career
            "position_name_tks": career.get("current_position"),
            "corporation_name_tks": career.get("current_company"),
            "industry_name_tks": career.get("industry"),
            "work_exp_flt": career.get("work_experience_years"),
            "expect_position_name_tks": career.get("expected_position"),
            "expect_city_names_tks": career.get("expected_city"),
            # Education
            "highest_degree_kwd": derived.get("highest_degree"),
            "school_name_tks": " ".join(e.get("institution", "") for e in education),
            "major_tks": " ".join(e.get("major", "") for e in education if e.get("major")),
            "edu_end_int": cls._get_graduation_year(education),
            # Experience
            "corp_nm_tks": " ".join(e.get("company", "") for e in experience),
            # Skills
            "skill_kwd": skills.get("technical", []) + skills.get("soft", []),
            "certificate_kwd": skills.get("certifications", []),
            "language_kwd": [
                lang.get("language") for lang in skills.get("languages", [])
            ],
            # Metadata
            "integerity_flt": extracted.get("integrity_score", 0.0),
            "tag_kwd": extracted.get("tags", []),
        }

        # Add first degree info
        first = derived.get("first_degree", {})
        if first:
            ragflow["first_school_name_tks"] = first.get("institution")
            ragflow["first_degree_kwd"] = first.get("degree")
            ragflow["first_major_tks"] = first.get("major")

        # Remove None values
        return {k: v for k, v in ragflow.items() if v is not None}

    @classmethod
    def _get_graduation_year(cls, education: List[Dict]) -> Optional[int]:
        """Get most recent graduation year."""
        years = []
        for edu in education:
            end = edu.get("end_date")
            if end and end.lower() != "present":
                try:
                    year = int(end.split("-")[0])
                    years.append(year)
                except (ValueError, IndexError):
                    continue
        return max(years) if years else None
