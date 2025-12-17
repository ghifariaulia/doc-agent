"""
Documentation Reviewer Module
Critiques generated documentation against source code analysis
"""

from typing import List, Tuple
from .analyzers.base import EndpointInfo
from .groq_service import GroqService


class DocumentationReviewer:
    """Reviewer agent that critiques and refines documentation"""

    def __init__(self, groq_service: GroqService):
        self.groq_service = groq_service

    def review(self, doc_content: str, endpoints: List[EndpointInfo]) -> Tuple[bool, str]:
        """
        Review the generated documentation.

        Args:
            doc_content: The markdown content to review
            endpoints: The source of truth (code analysis)

        Returns:
            Tuple[bool, str]: (passed_review, critique_or_refined_content)
        """

        # 1. Critique
        critique = self.groq_service.critique_documentation(doc_content, endpoints)

        # Check if critique indicates issues (heuristic: look for "PASS" vs "FAIL" or specific keywords)
        # For this implementation, we'll ask the LLM to output "STATUS: PASS" or "STATUS: FAIL"

        if "STATUS: PASS" in critique:
            return True, doc_content

        # 2. Refine (if failed)
        refined_content = self.groq_service.refine_documentation(doc_content, critique, endpoints)
        return False, refined_content
