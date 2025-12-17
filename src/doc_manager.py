"""
Documentation Manager Module
Handles creation and updating of documentation files
"""

import json
import re
from pathlib import Path
from typing import List

from .analyzers.base import EndpointInfo
from .groq_service import GroqService


class DocumentationManager:
    """Manages API documentation generation and updates"""

    def __init__(self, output_path: str, groq_service: GroqService):
        self.output_path = Path(output_path)
        self.groq_service = groq_service
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def generate_or_update(self, endpoints: List[EndpointInfo], project_name: str = "API") -> str:
        """
        Generate new documentation or smartly update existing one

        Args:
            endpoints: List of endpoint information
            project_name: Name of the project

        Returns:
            Path to the generated/updated documentation
        """
        if self.output_path.exists():
            return self._update_existing_documentation(endpoints, project_name)
        else:
            return self._generate_documentation(endpoints, project_name)

    def _update_existing_documentation(self, endpoints: List[EndpointInfo], project_name: str) -> str:
        """Update existing documentation by replacing the Endpoints section"""

        print(f"🔄 Updating existing documentation...")

        # Read existing documentation
        with open(self.output_path, "r", encoding="utf-8") as f:
            existing_content = f.read()

        # Generate new API documentation content
        new_api_docs = self.groq_service.generate_documentation(endpoints, project_name)

        # Try to find and replace the Endpoints section
        updated_content = self._replace_endpoints_section(existing_content, new_api_docs)

        # Write updated content
        with open(self.output_path, "w", encoding="utf-8") as f:
            f.write(updated_content)

        print(f"✅ Documentation updated: {self.output_path}")
        return str(self.output_path)

    def _replace_endpoints_section(self, existing: str, new_api_docs: str) -> str:
        """
        Find and replace the Endpoints section in existing markdown.
        Looks for headers like "## Endpoints", "## API Endpoints", "## API Reference"
        """

        # Common section headers to look for
        patterns = [
            r'(^|\n)(##\s+Endpoints\s*\n)',
            r'(^|\n)(##\s+API\s+Endpoints\s*\n)',
            r'(^|\n)(##\s+API\s+Reference\s*\n)',
            r'(^|\n)(##\s+API\s*\n)',
        ]

        # Try to find the endpoints section
        for pattern in patterns:
            match = re.search(pattern, existing, re.IGNORECASE)
            if match:
                # Found the section - replace from this header to the end or next ## header
                start = match.end()

                # Find the next ## level header (end of endpoints section)
                next_section = re.search(r'\n##\s+[^#]', existing[start:])
                if next_section:
                    end = start + next_section.start()
                    # Preserve content before, replace section, preserve content after
                    return existing[: match.start() + 1] + new_api_docs.lstrip() + "\n" + existing[end:]
                else:
                    # No next section - replace to end of file
                    return existing[: match.start() + 1] + new_api_docs.lstrip()

        # No endpoints section found - append at the end
        print("ℹ️  No existing Endpoints section found, appending to end")
        return existing.rstrip() + "\n\n" + new_api_docs

    def _generate_documentation(self, endpoints: List[EndpointInfo], project_name: str) -> str:
        """Generate documentation from endpoints"""

        print(f"📝 Generating documentation for {len(endpoints)} endpoints...")

        # Generate clean markdown with Groq AI
        doc_content = self.groq_service.generate_documentation(endpoints, project_name)

        # Write clean markdown to file (no markers)
        with open(self.output_path, "w", encoding="utf-8") as f:
            f.write(doc_content)

        print(f"✅ Documentation generated: {self.output_path}")
        return str(self.output_path)

    def save_endpoint_analysis(self, endpoints: List[EndpointInfo], output_file: str):
        """Save raw endpoint analysis to JSON file (for debugging/inspection)"""

        analysis_path = Path(output_file)
        analysis_path.parent.mkdir(parents=True, exist_ok=True)

        with open(analysis_path, "w", encoding="utf-8") as f:
            json.dump([ep.to_dict() for ep in endpoints], f, indent=2)

        print(f"📊 Endpoint analysis saved: {analysis_path}")
