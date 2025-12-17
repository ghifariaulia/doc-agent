"""
Base Analyzer Module
Defines abstract interface for all framework analyzers
"""

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class EndpointParameter:
    """Represents a parameter in an API endpoint"""

    name: str
    param_type: str  # path, query, body, header
    data_type: str
    required: bool = True
    default: Optional[str] = None
    description: Optional[str] = None


@dataclass
class EndpointInfo:
    """Represents information about an API endpoint"""

    path: str
    method: str
    function_name: str
    summary: Optional[str] = None
    description: Optional[str] = None
    parameters: List[EndpointParameter] = None
    request_model: Optional[str] = None
    response_model: Optional[str] = None
    tags: List[str] = None
    status_code: int = 200
    file_path: str = ""
    line_number: int = 0

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []
        if self.tags is None:
            self.tags = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert endpoint info to dictionary"""
        result = asdict(self)
        # Parameters are already converted by asdict, but ensure they're proper dicts
        result["parameters"] = [asdict(p) if isinstance(p, EndpointParameter) else p for p in self.parameters]
        return result


class BaseAnalyzer(ABC):
    """Abstract base class for framework-specific API analyzers"""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.endpoints: List[EndpointInfo] = []

    @abstractmethod
    def analyze(self) -> List[EndpointInfo]:
        """
        Analyze project code and extract API endpoints

        Returns:
            List of endpoint information
        """
        pass

    def get_endpoints_as_json(self) -> str:
        """Get endpoints as JSON string"""
        return json.dumps([ep.to_dict() for ep in self.endpoints], indent=2)

    def save_analysis(self, output_path: str):
        """Save analysis results to a JSON file"""
        with open(output_path, "w") as f:
            f.write(self.get_endpoints_as_json())

    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during analysis"""
        skip_patterns = ["__pycache__", "venv", "env", ".venv", ".git", "test_", "tests", "migrations"]
        return any(pattern in str(file_path) for pattern in skip_patterns)

    def _parse_docstring(self, docstring: str) -> tuple[Optional[str], Optional[str]]:
        """Parse docstring to extract summary and description"""
        if not docstring:
            return None, None

        lines = docstring.strip().split("\n")
        summary = lines[0] if lines else None
        description = "\n".join(lines[1:]).strip() if len(lines) > 1 else None

        return summary, description
