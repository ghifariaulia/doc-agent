"""
Groq Service Module
Handles integration with Groq API for AI-powered documentation generation
"""

import os
from typing import List, Optional

from dotenv import load_dotenv
from groq import Groq

from .analyzer import EndpointInfo


class GroqService:
    """Service for interacting with Groq API to generate documentation"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        load_dotenv()

        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found. Please set it in .env file or pass it as parameter.")

        self.model = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.client = Groq(api_key=self.api_key)

    def generate_documentation(self, endpoints: List[EndpointInfo], project_name: str = "API") -> str:
        """Generate complete API documentation from endpoints"""

        prompt = self._create_documentation_prompt(endpoints, project_name)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert technical writer specializing in API documentation. "
                        "Generate clear, comprehensive, and well-structured API documentation in Markdown format. "
                        "Include examples, describe all parameters, and provide useful context for developers.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=5000,
            )

            return response.choices[0].message.content

        except Exception as e:
            raise Exception(f"Error generating documentation with Groq API: {e}")

    def update_endpoint_documentation(self, endpoint: EndpointInfo, existing_doc: str = "") -> str:
        """Generate or update documentation for a specific endpoint"""

        prompt = self._create_endpoint_update_prompt(endpoint, existing_doc)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert technical writer. Update or create documentation for a specific API endpoint. "
                        "Maintain consistent style and format. If existing documentation is provided, preserve the good parts "
                        "and update only what's necessary based on the code changes.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=3000,
            )

            return response.choices[0].message.content

        except Exception as e:
            raise Exception(f"Error updating endpoint documentation: {e}")

    def _create_documentation_prompt(self, endpoints: List[EndpointInfo], project_name: str) -> str:
        """Create prompt for full documentation generation"""

        endpoints_info = []
        for ep in endpoints:
            ep_str = f"""
### {ep.method} {ep.path}
- **Function**: {ep.function_name}
- **Summary**: {ep.summary or "Not provided"}
- **Description**: {ep.description or "Not provided"}
- **Tags**: {", ".join(ep.tags) if ep.tags else "None"}
- **Status Code**: {ep.status_code}
"""

            if ep.parameters:
                ep_str += "\n**Parameters**:\n"
                for param in ep.parameters:
                    ep_str += f"  - `{param.name}` ({param.param_type}): {param.data_type}"
                    if not param.required:
                        ep_str += f" [Optional, default: {param.default}]"
                    ep_str += "\n"

            if ep.request_model:
                ep_str += f"\n**Request Model**: {ep.request_model}\n"

            if ep.response_model:
                ep_str += f"**Response Model**: {ep.response_model}\n"

            endpoints_info.append(ep_str)

        prompt = f"""
Generate comprehensive API documentation for the "{project_name}" project.

Please create documentation in Markdown format with the following structure:
1. Overview section with a brief description of the API
2. Base URL and authentication information (if applicable)
3. Detailed endpoint documentation organized by tags/categories
4. For each endpoint, include:
   - HTTP method and path
   - Description and purpose
   - Request parameters with types and descriptions
   - Request body schema (if applicable)
   - Response format and status codes
   - Example requests and responses (use realistic sample data)
   - Error responses

Here are the extracted endpoints:

{chr(10).join(endpoints_info)}

Create professional, developer-friendly documentation that is easy to understand and use.
Add realistic curl examples for each endpoint.
"""

        return prompt

    def _create_endpoint_update_prompt(self, endpoint: EndpointInfo, existing_doc: str) -> str:
        """Create prompt for updating single endpoint documentation"""

        endpoint_details = f"""
**Endpoint**: {endpoint.method} {endpoint.path}
**Function**: {endpoint.function_name}
**Summary**: {endpoint.summary or "Not provided"}
**Description**: {endpoint.description or "Not provided"}
**Tags**: {", ".join(endpoint.tags) if endpoint.tags else "None"}
**Status Code**: {endpoint.status_code}
"""

        if endpoint.parameters:
            endpoint_details += "\n**Parameters**:\n"
            for param in endpoint.parameters:
                endpoint_details += f"  - `{param.name}` ({param.param_type}): {param.data_type}"
                if not param.required:
                    endpoint_details += f" [Optional, default: {param.default}]"
                endpoint_details += "\n"

        if endpoint.request_model:
            endpoint_details += f"\n**Request Model**: {endpoint.request_model}\n"

        if endpoint.response_model:
            endpoint_details += f"**Response Model**: {endpoint.response_model}\n"

        if existing_doc:
            prompt = f"""
Update the existing documentation for this API endpoint based on the current code.

**Current Endpoint Information**:
{endpoint_details}

**Existing Documentation**:
{existing_doc}

Please update the documentation to reflect any changes while maintaining the overall style and structure.
If the endpoint hasn't changed significantly, preserve the existing content.
Include updated examples if parameters or models have changed.
Return the complete updated documentation section for this endpoint in Markdown format.
"""
        else:
            prompt = f"""
Create documentation for this new API endpoint:

{endpoint_details}

Generate a comprehensive documentation section in Markdown format including:
- Endpoint description and purpose
- All parameters with descriptions
- Request/response examples
- Possible error responses
- Usage notes if applicable
"""

        return prompt

    def summarize_changes(self, old_endpoints: List[EndpointInfo], new_endpoints: List[EndpointInfo]) -> str:
        """Generate a summary of changes between old and new endpoints"""

        old_paths = {f"{ep.method} {ep.path}": ep for ep in old_endpoints}
        new_paths = {f"{ep.method} {ep.path}": ep for ep in new_endpoints}

        added = [path for path in new_paths if path not in old_paths]
        removed = [path for path in old_paths if path not in new_paths]
        modified = []

        for path in new_paths:
            if path in old_paths:
                # Simple comparison - could be enhanced
                if (
                    old_paths[path].parameters != new_paths[path].parameters
                    or old_paths[path].request_model != new_paths[path].request_model
                    or old_paths[path].response_model != new_paths[path].response_model
                ):
                    modified.append(path)

        summary = "## API Documentation Changes\n\n"

        if added:
            summary += "### Added Endpoints\n"
            for path in added:
                summary += f"- `{path}`\n"
            summary += "\n"

        if removed:
            summary += "### Removed Endpoints\n"
            for path in removed:
                summary += f"- `{path}`\n"
            summary += "\n"

        if modified:
            summary += "### Modified Endpoints\n"
            for path in modified:
                summary += f"- `{path}`\n"
            summary += "\n"

        if not (added or removed or modified):
            summary += "No changes detected.\n"

        return summary

    def critique_documentation(self, doc_content: str, endpoints: List[EndpointInfo]) -> str:
        """Critique the generated documentation against the code analysis"""

        endpoints_summary = self._create_documentation_prompt(endpoints, "API Context")

        prompt = f"""
        You are a strict API Documentation Reviewer. Your job is to check the generated documentation against the actual API structure.
        
        **Actual Code Analysis (Truth)**:
        {endpoints_summary}
        
        **Generated Documentation**:
        {doc_content}
        
        Review the documentation for:
        1. **Accuracy**: Do all endpoints from the code appear in the docs?
        2. **Correctness**: Do parameters and types match exactly?
        3. **Missing Info**: Are any required parameters marked as optional or vice-versa?
        
        If the documentation is accurate, respond with ONLY: "STATUS: PASS"
        
        If there are issues, respond with:
        "STATUS: FAIL"
        [List of specific issues found]
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a QA for API documentation."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error critiquing documentation: {e}")
            return "STATUS: PASS"  # Fail open if API fails

    def refine_documentation(self, doc_content: str, critique: str, endpoints: List[EndpointInfo]) -> str:
        """Refine documentation based on critique"""

        endpoints_summary = self._create_documentation_prompt(endpoints, "API Context")

        prompt = f"""
        You need to fix the API documentation based on a critique.
        
        **Actual Code Analysis**:
        {endpoints_summary}
        
        **Current Draft**:
        {doc_content}
        
        **Critique (Issues to Fix)**:
        {critique}
        
        Please rewrite the documentation to address all the issues in the critique.
        Return the COMPLETE corrected markdown.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert technical writer fixing documentation errors."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error refining documentation: {e}")
            return doc_content  # Return original if refinement fails
