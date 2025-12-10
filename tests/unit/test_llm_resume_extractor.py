"""
Tests for LLM-based resume extraction.

Tests the LLMResumeExtractor class that uses LLM to extract structured
fields from resumes, matching RAGFlow's field schema.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from backend.processors.llm_resume_extractor import (
    LLMResumeExtractor,
    _get_model_string,
    _get_litellm_kwargs,
)


class TestGetModelString:
    """Tests for _get_model_string helper."""

    def test_uses_llm_model_string_if_set(self):
        """Should use LLM_MODEL_STRING if configured."""
        with patch("backend.processors.llm_resume_extractor.settings") as mock_settings:
            mock_settings.LLM_MODEL_STRING = "custom/model"
            mock_settings.LLM_PROVIDER = "openai"
            mock_settings.CHAT_MODEL = "gpt-4"

            result = _get_model_string()
            assert result == "custom/model"

    def test_constructs_from_provider_and_model(self):
        """Should construct from LLM_PROVIDER/CHAT_MODEL if LLM_MODEL_STRING not set."""
        with patch("backend.processors.llm_resume_extractor.settings") as mock_settings:
            mock_settings.LLM_MODEL_STRING = ""
            mock_settings.LLM_PROVIDER = "openai"
            mock_settings.CHAT_MODEL = "gpt-4o-mini"

            result = _get_model_string()
            assert result == "openai/gpt-4o-mini"


class TestGetLitellmKwargs:
    """Tests for _get_litellm_kwargs helper."""

    def test_includes_timeout(self):
        """Should include timeout from settings."""
        with patch("backend.processors.llm_resume_extractor.settings") as mock_settings:
            mock_settings.LLM_MODEL_STRING = "openai/gpt-4"
            mock_settings.LLM_TIMEOUT = 30
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_settings.LLM_API_BASE = ""

            result = _get_litellm_kwargs()
            assert result["timeout"] == 30

    def test_includes_api_key_for_openai(self):
        """Should include API key for OpenAI models."""
        with patch("backend.processors.llm_resume_extractor.settings") as mock_settings:
            mock_settings.LLM_MODEL_STRING = "openai/gpt-4"
            mock_settings.LLM_TIMEOUT = 30
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_settings.LLM_API_BASE = ""

            result = _get_litellm_kwargs()
            assert result["api_key"] == "test-key"

    def test_includes_api_base_if_set(self):
        """Should include API base if configured."""
        with patch("backend.processors.llm_resume_extractor.settings") as mock_settings:
            mock_settings.LLM_MODEL_STRING = "openai/gpt-4"
            mock_settings.LLM_TIMEOUT = 30
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_settings.LLM_API_BASE = "https://custom.api.com"

            result = _get_litellm_kwargs()
            assert result["api_base"] == "https://custom.api.com"


class TestLLMResumeExtractor:
    """Tests for LLMResumeExtractor class."""

    @pytest.fixture
    def sample_resume_content(self):
        """Sample resume text for testing."""
        return """
John Smith
Software Engineer
john.smith@email.com | (555) 123-4567
San Francisco, CA

PROFESSIONAL SUMMARY
Experienced software engineer with 8+ years of experience in full-stack development.

EXPERIENCE
Senior Software Engineer
Tech Corp Inc., San Francisco, CA
January 2020 - Present
- Lead development of microservices architecture
- Mentored junior developers
- Improved system performance by 40%

Software Engineer
StartUp LLC, San Francisco, CA
June 2016 - December 2019
- Developed REST APIs using Python and Node.js
- Implemented CI/CD pipelines

EDUCATION
Master of Science in Computer Science
Stanford University, 2016
GPA: 3.8

Bachelor of Science in Computer Science
UC Berkeley, 2014

SKILLS
Python, JavaScript, TypeScript, React, Node.js, PostgreSQL, Docker, Kubernetes, AWS

CERTIFICATIONS
AWS Solutions Architect Professional
Kubernetes Administrator (CKA)
"""

    @pytest.fixture
    def mock_llm_response(self):
        """Mock LLM response with extracted resume data."""
        return {
            "personal": {
                "name": "John Smith",
                "email": "john.smith@email.com",
                "phone": "(555) 123-4567",
                "location": "San Francisco, CA",
            },
            "career": {
                "current_position": "Senior Software Engineer",
                "current_company": "Tech Corp Inc.",
                "work_experience_years": 8.0,
            },
            "education": [
                {
                    "institution": "Stanford University",
                    "degree": "Master of Science",
                    "major": "Computer Science",
                    "end_date": "2016",
                },
                {
                    "institution": "UC Berkeley",
                    "degree": "Bachelor of Science",
                    "major": "Computer Science",
                    "end_date": "2014",
                },
            ],
            "experience": [
                {
                    "company": "Tech Corp Inc.",
                    "position": "Senior Software Engineer",
                    "start_date": "2020-01",
                    "end_date": "Present",
                },
                {
                    "company": "StartUp LLC",
                    "position": "Software Engineer",
                    "start_date": "2016-06",
                    "end_date": "2019-12",
                },
            ],
            "skills": {
                "technical": ["Python", "JavaScript", "TypeScript", "React"],
                "certifications": ["AWS Solutions Architect", "CKA"],
            },
        }

    def test_empty_result_structure(self):
        """Test _empty_result returns correct structure."""
        result = LLMResumeExtractor._empty_result()

        assert "personal" in result
        assert "career" in result
        assert "education" in result
        assert "experience" in result
        assert "skills" in result
        assert "integrity_score" in result
        assert result["integrity_score"] == 0.0

    def test_calculate_integrity_empty(self):
        """Test integrity score for empty extraction."""
        empty = LLMResumeExtractor._empty_result()
        score = LLMResumeExtractor._calculate_integrity(empty)
        assert score == 0.0

    def test_calculate_integrity_partial(self):
        """Test integrity score for partial extraction."""
        partial = {
            "personal": {"name": "John", "email": "john@test.com"},
            "career": {},
            "education": [],
            "experience": [],
        }
        score = LLMResumeExtractor._calculate_integrity(partial)
        assert 0.0 < score < 0.5

    def test_calculate_integrity_complete(self):
        """Test integrity score for complete extraction."""
        complete = {
            "personal": {
                "name": "John",
                "email": "john@test.com",
                "phone": "123",
                "location": "SF",
            },
            "career": {
                "current_position": "Engineer",
                "current_company": "Corp",
                "work_experience_years": 5,
            },
            "education": [{"degree": "BS", "institution": "Uni"}],
            "experience": [{"company": "Corp", "responsibilities": "Work"}],
        }
        score = LLMResumeExtractor._calculate_integrity(complete)
        assert score > 0.7

    def test_get_highest_degree_phd(self):
        """Test highest degree detection for PhD."""
        education = [
            {"degree": "Bachelor of Science"},
            {"degree": "PhD in Computer Science"},
        ]
        result = LLMResumeExtractor._get_highest_degree(education)
        assert "PhD" in result

    def test_get_highest_degree_master(self):
        """Test highest degree detection for Master's."""
        education = [
            {"degree": "Bachelor of Science"},
            {"degree": "Master of Science"},
        ]
        result = LLMResumeExtractor._get_highest_degree(education)
        assert "Master" in result

    def test_get_highest_degree_bachelor(self):
        """Test highest degree detection for Bachelor's only."""
        education = [{"degree": "Bachelor of Science"}]
        result = LLMResumeExtractor._get_highest_degree(education)
        assert "Bachelor" in result

    def test_calculate_work_years(self):
        """Test work years calculation."""
        experience = [
            {"start_date": "2020-01"},
            {"start_date": "2018-06"},
            {"start_date": "2015-01"},
        ]
        years = LLMResumeExtractor._calculate_work_years(experience)
        # Should be approximately current_year - 2015
        assert years is not None
        assert years >= 9  # At least since 2015

    def test_calculate_work_years_empty(self):
        """Test work years calculation with empty experience."""
        years = LLMResumeExtractor._calculate_work_years([])
        assert years is None

    def test_generate_tags_phd(self):
        """Test tag generation for PhD."""
        extracted = {
            "derived": {"highest_degree": "PhD in Computer Science"},
            "career": {"work_experience_years": 10},
            "skills": {"technical": [], "certifications": []},
        }
        tags = LLMResumeExtractor._generate_tags(extracted)
        assert "PhD" in tags

    def test_generate_tags_senior(self):
        """Test tag generation for senior experience."""
        extracted = {
            "derived": {},
            "career": {"work_experience_years": 12},
            "skills": {"technical": [], "certifications": []},
        }
        tags = LLMResumeExtractor._generate_tags(extracted)
        assert "Senior (10+ years)" in tags

    def test_generate_tags_certified(self):
        """Test tag generation for certifications."""
        extracted = {
            "derived": {},
            "career": {},
            "skills": {"certifications": ["AWS", "CKA"]},
        }
        tags = LLMResumeExtractor._generate_tags(extracted)
        assert "Certified Professional" in tags

    def test_to_ragflow_format(self, mock_llm_response):
        """Test conversion to RAGFlow field format."""
        # Add required fields
        mock_llm_response["derived"] = {"highest_degree": "Master of Science"}
        mock_llm_response["integrity_score"] = 0.85
        mock_llm_response["tags"] = ["Senior"]

        result = LLMResumeExtractor.to_ragflow_format(mock_llm_response)

        # Check RAGFlow-style field names
        assert "name_kwd" in result
        assert result["name_kwd"] == "John Smith"
        assert "email_tks" in result
        assert "phone_kwd" in result
        assert "position_name_tks" in result
        assert "corporation_name_tks" in result
        assert "highest_degree_kwd" in result
        assert "skill_kwd" in result
        assert "certificate_kwd" in result

    def test_parse_json_response_valid(self):
        """Test JSON parsing with valid response."""
        response = '{"personal": {"name": "John"}, "education": []}'
        result = LLMResumeExtractor._parse_json_response(response)
        assert result["personal"]["name"] == "John"

    def test_parse_json_response_with_markdown(self):
        """Test JSON parsing with markdown code blocks."""
        response = '```json\n{"personal": {"name": "John"}}\n```'
        result = LLMResumeExtractor._parse_json_response(response)
        assert result["personal"]["name"] == "John"

    def test_parse_json_response_invalid(self):
        """Test JSON parsing with invalid response."""
        response = "not valid json"
        result = LLMResumeExtractor._parse_json_response(response)
        assert result["integrity_score"] == 0.0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_extract_real_resume_aayushi(self):
        """Test extraction with real resume PDF - Aayushi."""
        from pathlib import Path

        # Get path to test resume
        test_docs = Path(__file__).parent.parent.parent / "test_docs"
        resume_path = test_docs / "AayushiChauhan_CV_2025.pdf"

        if not resume_path.exists():
            pytest.skip(f"Test resume not found: {resume_path}")

        # Parse PDF to text using docling
        from backend.parsers.docling_parser import DoclingParser
        parser = DoclingParser()
        parsed = await parser.parse(str(resume_path))

        # Extract text content from parser result
        text_content = parsed["content"] if isinstance(parsed, dict) else parsed

        # Extract using LLM
        result = await LLMResumeExtractor.extract(text_content)

        # Validate extraction
        assert result["integrity_score"] > 0.3, f"Should extract meaningful data, got: {result}"
        assert result["personal"].get("name"), f"Should extract name, got: {result['personal']}"
        assert result["personal"].get("email") or result["personal"].get("phone"), "Should extract contact info"
        assert len(result["education"]) > 0, "Should extract education"
        assert len(result["experience"]) > 0, "Should extract experience"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_extract_real_resume_raghav(self):
        """Test extraction with real resume PDF - Raghav."""
        from pathlib import Path

        # Get path to test resume
        test_docs = Path(__file__).parent.parent.parent / "test_docs"
        resume_path = test_docs / "Raghav Patnecha_CV_AI_TPM_compressed.pdf"

        if not resume_path.exists():
            pytest.skip(f"Test resume not found: {resume_path}")

        # Parse PDF to text using docling
        from backend.parsers.docling_parser import DoclingParser
        parser = DoclingParser()
        parsed = await parser.parse(str(resume_path))

        # Extract text content from parser result
        text_content = parsed["content"] if isinstance(parsed, dict) else parsed

        # Extract using LLM
        result = await LLMResumeExtractor.extract(text_content)

        # Validate extraction
        assert result["integrity_score"] > 0.3, f"Should extract meaningful data, got: {result}"
        assert result["personal"].get("name"), f"Should extract name, got: {result['personal']}"
        assert "tags" in result, "Should generate tags"
        assert "derived" in result, "Should have derived fields"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_extract_real_resume_dhairya(self):
        """Test extraction with real resume PDF - Dhairya."""
        from pathlib import Path

        # Get path to test resume
        test_docs = Path(__file__).parent.parent.parent / "test_docs"
        resume_path = test_docs / "Dhairya Prakash Professional Marketing Resume Creation.pdf"

        if not resume_path.exists():
            pytest.skip(f"Test resume not found: {resume_path}")

        # Parse PDF to text using docling
        from backend.parsers.docling_parser import DoclingParser
        parser = DoclingParser()
        parsed = await parser.parse(str(resume_path))

        # Extract text content from parser result
        text_content = parsed["content"] if isinstance(parsed, dict) else parsed

        # Extract using LLM
        result = await LLMResumeExtractor.extract(text_content)

        # Validate extraction
        assert result["integrity_score"] > 0.3, f"Should extract meaningful data, got: {result}"
        assert result["personal"].get("name"), f"Should extract name, got: {result['personal']}"

    @pytest.mark.asyncio
    async def test_extract_with_sample_content(self, sample_resume_content):
        """Test extraction with sample resume text content."""
        result = await LLMResumeExtractor.extract(sample_resume_content)

        # Should extract basic info from sample content
        assert "integrity_score" in result
        assert "personal" in result
        assert "education" in result
        assert "experience" in result

        # If extraction succeeded, verify structure
        if result["integrity_score"] > 0:
            assert isinstance(result["personal"], dict)
            assert isinstance(result["education"], list)
            assert isinstance(result["experience"], list)
