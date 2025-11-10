"""
Google Gemini API integration for compliance analysis.
Handles structured compliance checking and analysis using Gemini models.
"""

import asyncio
import logging
from typing import Optional

import google.generativeai as genai
from pydantic import BaseModel, Field

from complianceguard.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# Structured Output Models

class ComplianceCheckResult(BaseModel):
    """Structured output from Gemini compliance analysis."""

    compliant: bool = Field(
        ..., description="Whether the documents meet the compliance requirement"
    )
    confidence_score: float = Field(
        ..., description="Confidence in the assessment (0-1)"
    )
    status: str = Field(
        ..., description="Status: 'compliant', 'non_compliant', or 'partial'"
    )
    framework_evidence: str = Field(
        ..., description="Relevant quote from the compliance framework document"
    )
    document_evidence: str = Field(
        ..., description="Relevant quote from the analyzed document(s)"
    )
    gap_analysis: str = Field(
        ..., description="What's missing or different between framework and documents"
    )
    remediation: str = Field(
        ..., description="Suggested actions to achieve full compliance"
    )
    risk_level: str = Field(
        ..., description="Risk severity: 'critical', 'high', 'medium', 'low'"
    )
    explanation: str = Field(
        ..., description="Detailed explanation of the compliance assessment"
    )


class GeminiClient:
    """Client for Google Gemini API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """
        Initialize Gemini client.

        Args:
            api_key: Gemini API key (defaults to settings)
            model_name: Model name (defaults to settings)
            temperature: Temperature for generation (defaults to settings)
            max_tokens: Max tokens for generation (defaults to settings)
        """
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = model_name or settings.gemini_model
        self.temperature = temperature or settings.gemini_temperature
        self.max_tokens = max_tokens or settings.gemini_max_tokens
        self.timeout = settings.gemini_timeout_seconds
        self.max_retries = settings.gemini_max_retries

        if not self.api_key:
            logger.warning("Gemini API key not configured")
        else:
            # Configure the Gemini API
            genai.configure(api_key=self.api_key)

        # Initialize model
        self.model = None
        if self.api_key:
            try:
                self.model = genai.GenerativeModel(self.model_name)
                logger.info(f"Initialized Gemini model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini model: {e}")

    async def check_compliance(
        self,
        requirement: str,
        framework_text: str,
        document_text: str,
    ) -> ComplianceCheckResult:
        """
        Check compliance of document against a framework requirement.

        Args:
            requirement: The compliance requirement to check
            framework_text: Relevant text from the compliance framework
            document_text: Relevant text from the document(s) to analyze

        Returns:
            Structured compliance check result

        Raises:
            ValueError: If API key is not configured
            Exception: If API call fails
        """
        if not self.api_key or not self.model:
            raise ValueError(
                "Gemini API key not configured. Set GEMINI_API_KEY environment variable."
            )

        # Build the prompt
        prompt = self._build_compliance_prompt(
            requirement, framework_text, document_text
        )

        # Make async request with retries
        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"Checking compliance with Gemini (attempt {attempt + 1}/{self.max_retries})"
                )

                # Run in thread pool since Gemini SDK is sync
                response = await asyncio.to_thread(
                    self._generate_with_schema,
                    prompt
                )

                logger.info("Successfully received compliance analysis from Gemini")
                return response

            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"Gemini API error (attempt {attempt + 1}/{self.max_retries}). "
                        f"Retrying in {wait_time} seconds... Error: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All retry attempts failed: {e}")
                    raise

    def _generate_with_schema(self, prompt: str) -> ComplianceCheckResult:
        """
        Generate response with structured output schema.

        Args:
            prompt: The prompt to send to Gemini

        Returns:
            Parsed ComplianceCheckResult
        """
        # Configure generation with schema
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=ComplianceCheckResult,
            temperature=self.temperature,
            max_output_tokens=self.max_tokens,
        )

        # Generate response
        response = self.model.generate_content(
            prompt,
            generation_config=generation_config
        )

        # Parse structured output
        result_data = response.text

        # If Gemini returns JSON string, parse it
        if isinstance(result_data, str):
            import json
            result_data = json.loads(result_data)

        # Create ComplianceCheckResult from dict
        result = ComplianceCheckResult(**result_data)

        return result

    def _build_compliance_prompt(
        self,
        requirement: str,
        framework_text: str,
        document_text: str,
    ) -> str:
        """
        Build the compliance checking prompt.

        Args:
            requirement: The compliance requirement
            framework_text: Framework document text
            document_text: Document text to analyze

        Returns:
            Formatted prompt string
        """
        prompt = f"""You are a compliance analyst expert. Your task is to analyze whether the provided document meets a specific compliance requirement from a regulatory framework.

**Compliance Requirement:**
{requirement}

**Framework Document (Reference Standard):**
{framework_text}

**Document to Analyze:**
{document_text}

**Instructions:**
1. Carefully compare the document content against the framework requirement.
2. Identify if the requirement is met (compliant), not met (non_compliant), or partially met (partial).
3. Extract exact quotes from both texts as evidence.
4. Perform a gap analysis explaining what's missing or different.
5. Provide specific remediation actions if not compliant.
6. Assess the risk level if the requirement is not met.
7. Give a confidence score for your assessment.

**Output Requirements:**
- Be objective and precise
- Use exact quotes from the source documents
- Focus on factual analysis, not opinions
- Provide actionable remediation steps
- Consider regulatory implications in risk assessment

Analyze the compliance status and provide a structured response."""

        return prompt


# Global client instance
_gemini_client: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    """
    Get or create global Gemini client instance.

    Returns:
        Gemini client instance
    """
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client


async def analyze_compliance(
    requirement: str,
    framework_text: str,
    document_text: str,
) -> ComplianceCheckResult:
    """
    Analyze compliance using Gemini API.

    Args:
        requirement: Compliance requirement to check
        framework_text: Framework document text
        document_text: Document text to analyze

    Returns:
        Compliance check result

    Raises:
        ValueError: If API key not configured
        Exception: If API call fails
    """
    client = get_gemini_client()
    return await client.check_compliance(requirement, framework_text, document_text)
