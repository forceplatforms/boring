"""
ComplianceGuard AI - SEC Cybersecurity Compliance Gap Detection System.

A modern, AI-powered system for detecting compliance violations in SEC filings
by comparing internal incident reports against public disclosures.
"""

__version__ = "0.1.0"
__author__ = "ComplianceGuard Team"
__email__ = "team@complianceguard.ai"

# Import key components for easier access
from complianceguard.config import settings, get_settings

__all__ = [
    "__version__",
    "settings",
    "get_settings",
]