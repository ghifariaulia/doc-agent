"""
Code Analyzer Module
Extracts API endpoints, routes, and models from FastAPI applications
"""

import ast
import json
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


class FastAPIAnalyzer:
    """Analyzes FastAPI application code to extract endpoint information"""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.endpoints: List[EndpointInfo] = []

    def analyze(self) -> List[EndpointInfo]:
        """Analyze all Python files in the project to extract API endpoints"""
        self.endpoints = []

        # Find all Python files
        python_files = list(self.project_path.rglob("*.py"))

        for file_path in python_files:
            if self._should_skip_file(file_path):
                continue

            self._analyze_file(file_path)

        return self.endpoints

    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during analysis"""
        skip_patterns = ["__pycache__", "venv", "env", ".git", "test_", "tests"]
        return any(pattern in str(file_path) for pattern in skip_patterns)

    def _analyze_file(self, file_path: Path):
        """Analyze a single Python file for FastAPI endpoints"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            # Look for FastAPI route decorators
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    endpoint = self._extract_endpoint_from_function(node, file_path)
                    if endpoint:
                        self.endpoints.append(endpoint)

        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")

    def _extract_endpoint_from_function(self, func_node: ast.FunctionDef, file_path: Path) -> Optional[EndpointInfo]:
        """Extract endpoint information from a function definition"""

        # Check if function has FastAPI route decorators
        http_methods = ["get", "post", "put", "delete", "patch", "options", "head"]

        for decorator in func_node.decorator_list:
            method, path = self._parse_decorator(decorator, http_methods)

            if method and path:
                # Extract docstring
                docstring = ast.get_docstring(func_node) or ""
                summary, description = self._parse_docstring(docstring)

                # Extract parameters
                parameters = self._extract_parameters(func_node)

                # Extract models
                request_model, response_model = self._extract_models(func_node, decorator)

                # Extract tags and status code
                tags = self._extract_tags(decorator)
                status_code = self._extract_status_code(decorator) or 200

                endpoint = EndpointInfo(
                    path=path,
                    method=method.upper(),
                    function_name=func_node.name,
                    summary=summary,
                    description=description,
                    parameters=parameters,
                    request_model=request_model,
                    response_model=response_model,
                    tags=tags,
                    status_code=status_code,
                    file_path=str(file_path.relative_to(self.project_path)),
                    line_number=func_node.lineno,
                )

                return endpoint

        return None

    def _parse_decorator(self, decorator: ast.expr, http_methods: List[str]) -> tuple[Optional[str], Optional[str]]:
        """Parse decorator to extract HTTP method and path"""

        if isinstance(decorator, ast.Call):
            # Handle @app.get("/path") or @router.post("/path")
            if isinstance(decorator.func, ast.Attribute):
                method = decorator.func.attr
                if method in http_methods:
                    # Get the path from first argument
                    if decorator.args and isinstance(decorator.args[0], ast.Constant):
                        path = decorator.args[0].value
                        return method, path

        return None, None

    def _parse_docstring(self, docstring: str) -> tuple[Optional[str], Optional[str]]:
        """Parse docstring to extract summary and description"""
        if not docstring:
            return None, None

        lines = docstring.strip().split("\n")
        summary = lines[0] if lines else None
        description = "\n".join(lines[1:]).strip() if len(lines) > 1 else None

        return summary, description

    def _extract_parameters(self, func_node: ast.FunctionDef) -> List[EndpointParameter]:
        """Extract parameters from function signature"""
        parameters = []

        # Get defaults mapping (defaults are aligned to the right of args)
        args = func_node.args.args
        defaults = func_node.args.defaults
        num_defaults = len(defaults)
        num_args = len(args)

        for i, arg in enumerate(args):
            if arg.arg in ["self", "cls"]:
                continue

            param_type = "query"  # Default
            data_type = "string"  # Default
            required = True
            default_value = None

            # Check if this arg has a default value
            default_offset = i - (num_args - num_defaults)
            if default_offset >= 0:
                required = False
                # Extract default value and ensure it's serializable
                default_node = defaults[default_offset]
                if isinstance(default_node, ast.Constant):
                    default_value = str(default_node.value) if default_node.value is not None else "None"
                else:
                    default_value = ast.unparse(default_node)

            # Try to get type annotation
            if arg.annotation:
                type_str = self._get_type_string(arg.annotation)
                data_type = type_str

                # Determine parameter type based on annotation
                if "Path" in type_str:
                    param_type = "path"
                elif "Body" in type_str:
                    param_type = "body"
                elif "Header" in type_str:
                    param_type = "header"

            param = EndpointParameter(
                name=arg.arg,
                param_type=param_type,
                data_type=data_type,
                required=required,
                default=default_value,
            )
            parameters.append(param)

        return parameters

    def _get_type_string(self, annotation: ast.expr) -> str:
        """Convert AST type annotation to string"""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Subscript):
            return ast.unparse(annotation)
        elif isinstance(annotation, ast.Attribute):
            return ast.unparse(annotation)
        return "Any"

    def _extract_models(self, func_node: ast.FunctionDef, decorator: ast.expr) -> tuple[Optional[str], Optional[str]]:
        """Extract request and response models"""
        request_model = None
        response_model = None

        # Check return annotation for response model
        if func_node.returns:
            response_model = self._get_type_string(func_node.returns)

        # Check decorator for response_model parameter
        if isinstance(decorator, ast.Call):
            for keyword in decorator.keywords:
                if keyword.arg == "response_model":
                    response_model = self._get_type_string(keyword.value)

        # Check function parameters for request body model
        for arg in func_node.args.args:
            if arg.annotation:
                type_str = self._get_type_string(arg.annotation)
                # If it's a Pydantic model (capitalized), it's likely the request body
                if type_str and type_str[0].isupper() and "Path" not in type_str and "Query" not in type_str:
                    request_model = type_str
                    break

        return request_model, response_model

    def _extract_tags(self, decorator: ast.expr) -> List[str]:
        """Extract tags from decorator"""
        tags = []

        if isinstance(decorator, ast.Call):
            for keyword in decorator.keywords:
                if keyword.arg == "tags":
                    if isinstance(keyword.value, ast.List):
                        for elt in keyword.value.elts:
                            if isinstance(elt, ast.Constant):
                                tags.append(elt.value)

        return tags

    def _extract_status_code(self, decorator: ast.expr) -> Optional[int]:
        """Extract status code from decorator"""
        if isinstance(decorator, ast.Call):
            for keyword in decorator.keywords:
                if keyword.arg == "status_code":
                    if isinstance(keyword.value, ast.Constant):
                        return keyword.value.value  # Return the actual value, not the Constant object
        return None

    def get_endpoints_as_json(self) -> str:
        """Get endpoints as JSON string"""
        return json.dumps([ep.to_dict() for ep in self.endpoints], indent=2)

    def save_analysis(self, output_path: str):
        """Save analysis results to a JSON file"""
        with open(output_path, "w") as f:
            f.write(self.get_endpoints_as_json())
