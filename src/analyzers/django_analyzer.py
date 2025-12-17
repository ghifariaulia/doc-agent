"""
Django Analyzer Module
Extracts API endpoints from Django and Django REST Framework applications
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional

from .base import BaseAnalyzer, EndpointInfo, EndpointParameter


class DjangoAnalyzer(BaseAnalyzer):
    """Analyzes Django/DRF application code to extract endpoint information"""

    def __init__(self, project_path: str):
        super().__init__(project_path)
        self.url_patterns: List[Dict] = []
        self.viewsets: Dict[str, any] = {}
        self.serializers: Dict[str, any] = {}

    def analyze(self) -> List[EndpointInfo]:
        """Analyze Django project to extract API endpoints"""
        self.endpoints = []

        # Find all Python files
        python_files = list(self.project_path.rglob("*.py"))

        # First pass: Extract serializers
        for file_path in python_files:
            if self._should_skip_file(file_path) or "serializers" not in str(file_path):
                continue
            self._extract_serializers(file_path)

        # Second pass: Extract ViewSets and APIViews
        for file_path in python_files:
            if self._should_skip_file(file_path) or "admin" in str(file_path):
                continue
            self._extract_views(file_path)

        # Third pass: Parse URL patterns
        for file_path in python_files:
            if "urls.py" in file_path.name:
                self._parse_url_patterns(file_path)

        # Match URL patterns to views and create endpoints
        self._create_endpoints_from_patterns()

        return self.endpoints

    def _extract_serializers(self, file_path: Path):
        """Extract DRF serializer information"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's a serializer class
                    if self._is_serializer_class(node):
                        serializer_name = node.name
                        fields = self._extract_serializer_fields(node)
                        self.serializers[serializer_name] = {
                            "fields": fields,
                            "file": str(file_path.relative_to(self.project_path)),
                        }

        except Exception as e:
            print(f"Error extracting serializers from {file_path}: {e}")

    def _is_serializer_class(self, node: ast.ClassDef) -> bool:
        """Check if a class is a DRF serializer"""
        for base in node.bases:
            base_name = ast.unparse(base) if hasattr(ast, "unparse") else ""
            if "Serializer" in base_name:
                return True
        return False

    def _extract_serializer_fields(self, node: ast.ClassDef) -> List[str]:
        """Extract field names from serializer class"""
        fields = []

        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        # It's a field assignment
                        fields.append(target.id)
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                # Type-annotated field
                fields.append(item.target.id)

        return fields

    def _extract_views(self, file_path: Path):
        """Extract ViewSets and APIViews from views files"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    view_type = self._get_view_type(node)

                    if view_type == "viewset":
                        self._extract_viewset(node, file_path)
                    elif view_type == "apiview":
                        self._extract_apiview(node, file_path)

                elif isinstance(node, ast.FunctionDef):
                    # Check for @api_view decorator
                    if self._has_api_view_decorator(node):
                        self._extract_function_based_view(node, file_path)

        except Exception as e:
            print(f"Error extracting views from {file_path}: {e}")

    def _get_view_type(self, node: ast.ClassDef) -> Optional[str]:
        """Determine if a class is a ViewSet or APIView"""
        for base in node.bases:
            base_name = ast.unparse(base) if hasattr(ast, "unparse") else ""
            if "ViewSet" in base_name:
                return "viewset"
            elif "APIView" in base_name or "GenericAPIView" in base_name:
                return "apiview"
        return None

    def _extract_viewset(self, node: ast.ClassDef, file_path: Path):
        """Extract information from a ViewSet class"""
        viewset_info = {
            "name": node.name,
            "file": str(file_path.relative_to(self.project_path)),
            "line": node.lineno,
            "serializer": self._get_serializer_class(node),
            "queryset": self._get_queryset_model(node),
            "actions": self._extract_viewset_actions(node),
            "custom_actions": self._extract_custom_actions(node),
            "docstring": ast.get_docstring(node),
        }

        self.viewsets[node.name] = viewset_info

    def _get_serializer_class(self, node: ast.ClassDef) -> Optional[str]:
        """Extract serializer_class attribute from ViewSet"""
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "serializer_class":
                        if isinstance(item.value, ast.Name):
                            return item.value.id
        return None

    def _get_queryset_model(self, node: ast.ClassDef) -> Optional[str]:
        """Extract model from queryset attribute"""
        # This is a simplified version - could be enhanced
        return None

    def _extract_viewset_actions(self, node: ast.ClassDef) -> List[str]:
        """Extract standard ViewSet action methods"""
        standard_actions = ["list", "retrieve", "create", "update", "partial_update", "destroy"]
        found_actions = []

        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name in standard_actions:
                found_actions.append(item.name)

        return found_actions

    def _extract_custom_actions(self, node: ast.ClassDef) -> List[Dict]:
        """Extract custom @action decorated methods"""
        custom_actions = []

        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                for decorator in item.decorator_list:
                    if self._is_action_decorator(decorator):
                        action_info = self._parse_action_decorator(decorator, item)
                        if action_info:
                            custom_actions.append(action_info)

        return custom_actions

    def _is_action_decorator(self, decorator: ast.expr) -> bool:
        """Check if decorator is @action"""
        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
            return decorator.func.id == "action"
        elif isinstance(decorator, ast.Name):
            return decorator.id == "action"
        return False

    def _parse_action_decorator(self, decorator: ast.expr, func: ast.FunctionDef) -> Optional[Dict]:
        """Parse @action decorator to extract methods and detail"""
        if not isinstance(decorator, ast.Call):
            return None

        methods = ["get"]  # Default
        detail = False

        for keyword in decorator.keywords:
            if keyword.arg == "methods":
                if isinstance(keyword.value, ast.List):
                    methods = [elt.value for elt in keyword.value.elts if isinstance(elt, ast.Constant)]
            elif keyword.arg == "detail":
                if isinstance(keyword.value, ast.Constant):
                    detail = keyword.value.value

        return {
            "name": func.name,
            "methods": methods,
            "detail": detail,
            "docstring": ast.get_docstring(func),
            "line": func.lineno,
        }

    def _extract_apiview(self, node: ast.ClassDef, file_path: Path):
        """Extract information from an APIView class"""
        # Store APIView info - will be matched with URL patterns later
        apiview_info = {
            "name": node.name,
            "file": str(file_path.relative_to(self.project_path)),
            "line": node.lineno,
            "methods": self._extract_apiview_methods(node),
            "docstring": ast.get_docstring(node),
        }

        self.viewsets[node.name] = apiview_info  # Reuse viewsets dict for simplicity

    def _extract_apiview_methods(self, node: ast.ClassDef) -> List[Dict]:
        """Extract HTTP method handlers from APIView"""
        http_methods = ["get", "post", "put", "patch", "delete", "head", "options"]
        methods = []

        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name in http_methods:
                methods.append(
                    {
                        "method": item.name.upper(),
                        "docstring": ast.get_docstring(item),
                        "line": item.lineno,
                    }
                )

        return methods

    def _has_api_view_decorator(self, node: ast.FunctionDef) -> bool:
        """Check if function has @api_view decorator"""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                if decorator.func.id == "api_view":
                    return True
            elif isinstance(decorator, ast.Name) and decorator.id == "api_view":
                return True
        return False

    def _extract_function_based_view(self, node: ast.FunctionDef, file_path: Path):
        """Extract function-based view with @api_view"""
        # Extract allowed methods from @api_view decorator
        methods = self._parse_api_view_decorator(node)

        if not methods:
            methods = ["GET"]  # Default

        # Store function-based view info (will be matched with URL patterns later)
        fbv_info = {
            "name": node.name,
            "file": str(file_path.relative_to(self.project_path)),
            "line": node.lineno,
            "methods": [
                {"method": m.upper(), "docstring": ast.get_docstring(node), "line": node.lineno} for m in methods
            ],
            "docstring": ast.get_docstring(node),
        }

        # Store in viewsets dict for simplicity (will be matched with URL patterns)
        self.viewsets[node.name] = fbv_info

    def _parse_api_view_decorator(self, node: ast.FunctionDef) -> List[str]:
        """Parse @api_view decorator to extract allowed HTTP methods"""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                if decorator.func.id == "api_view":
                    # Parse the methods list argument
                    if decorator.args and isinstance(decorator.args[0], ast.List):
                        methods = []
                        for elt in decorator.args[0].elts:
                            if isinstance(elt, ast.Constant):
                                methods.append(elt.value)
                        return methods
        return []

    def _parse_url_patterns(self, file_path: Path):
        """Parse URL patterns from urls.py file"""
        try:
            content = file_path.read_text(encoding="utf-8")

            # Look for router registrations (DRF) - handles views.ViewSetName pattern
            # Matches: router.register(r'products', views.ProductViewSet, basename='product')
            router_pattern = re.compile(r"router\.register\(r?['\"]([^'\"]+)['\"],\s*(?:views\.)?(\w+)")
            for match in router_pattern.finditer(content):
                url_prefix = match.group(1)
                viewset_name = match.group(2)

                # Skip if viewset_name is just 'basename' (from the keyword argument)
                if viewset_name == 'basename':
                    continue

                self.url_patterns.append(
                    {
                        "type": "router",
                        "prefix": url_prefix,
                        "viewset": viewset_name,
                        "file": str(file_path.relative_to(self.project_path)),
                    }
                )

            # Look for path() and re_path() patterns
            # Matches both: View.as_view() and function_name
            path_pattern = re.compile(r"path\(['\"](.+?)['\"],\s*(?:\w+\.)?(\w+)(?:\.as_view\(\))?")
            for match in path_pattern.finditer(content):
                url_path = match.group(1)
                view_name = match.group(2)

                # Skip common non-view names
                if view_name in ['include', 'path', 're_path', 'name', 'basename']:
                    continue

                self.url_patterns.append(
                    {
                        "type": "path",
                        "path": url_path,
                        "view": view_name,
                        "file": str(file_path.relative_to(self.project_path)),
                    }
                )

        except Exception as e:
            print(f"Error parsing URL patterns from {file_path}: {e}")

    def _create_endpoints_from_patterns(self):
        """Create EndpointInfo objects from matched URL patterns and views"""
        for pattern in self.url_patterns:
            if pattern["type"] == "router" and pattern["viewset"] in self.viewsets:
                viewset = self.viewsets[pattern["viewset"]]
                self._create_viewset_endpoints(pattern["prefix"], viewset)

            elif pattern["type"] == "path" and pattern["view"] in self.viewsets:
                view = self.viewsets[pattern["view"]]
                self._create_apiview_endpoints(pattern["path"], view)

    def _create_viewset_endpoints(self, prefix: str, viewset: Dict):
        """Create endpoints for a ViewSet"""
        # Standard actions mapping
        action_mappings = {
            "list": ("GET", f"/{prefix}/"),
            "create": ("POST", f"/{prefix}/"),
            "retrieve": ("GET", f"/{prefix}/{{id}}/"),
            "update": ("PUT", f"/{prefix}/{{id}}/"),
            "partial_update": ("PATCH", f"/{prefix}/{{id}}/"),
            "destroy": ("DELETE", f"/{prefix}/{{id}}/"),
        }

        # Check which actions exist (if not specified, assume all for ModelViewSet)
        actions = viewset.get("actions", [])
        if not actions:
            # Assume standard ModelViewSet actions
            actions = list(action_mappings.keys())

        # Create endpoints for standard actions
        for action in actions:
            if action in action_mappings:
                method, path = action_mappings[action]
                summary, description = self._parse_docstring(viewset.get("docstring", ""))

                endpoint = EndpointInfo(
                    path=path,
                    method=method,
                    function_name=action,
                    summary=summary or f"{action.title()} {prefix}",
                    description=description,
                    parameters=self._get_viewset_parameters(action),
                    request_model=viewset.get("serializer"),
                    response_model=viewset.get("serializer"),
                    tags=[prefix.title()],
                    status_code=200 if method == "GET" else 201 if method == "POST" else 200,
                    file_path=viewset["file"],
                    line_number=viewset["line"],
                )
                self.endpoints.append(endpoint)

        # Create endpoints for custom actions
        for custom_action in viewset.get("custom_actions", []):
            for method in custom_action["methods"]:
                path_suffix = (
                    f"{{id}}/{custom_action['name']}/" if custom_action["detail"] else f"{custom_action['name']}/"
                )
                path = f"/{prefix}/{path_suffix}"
                summary, description = self._parse_docstring(custom_action.get("docstring", ""))

                endpoint = EndpointInfo(
                    path=path,
                    method=method.upper(),
                    function_name=custom_action["name"],
                    summary=summary or f"{custom_action['name'].title()} {prefix}",
                    description=description,
                    parameters=[],
                    tags=[prefix.title()],
                    status_code=200,
                    file_path=viewset["file"],
                    line_number=custom_action["line"],
                )
                self.endpoints.append(endpoint)

    def _create_apiview_endpoints(self, path: str, view: Dict):
        """Create endpoints for an APIView"""
        # Check if it has methods (APIView) or actions (ViewSet mistakenly in this path)
        methods = view.get("methods", [])

        for method_info in methods:
            summary, description = self._parse_docstring(view.get("docstring", ""))

            endpoint = EndpointInfo(
                path=f"/{path}",
                method=method_info["method"],
                function_name=view["name"],
                summary=summary or f"{view['name']}",
                description=description,
                parameters=[],
                tags=["API"],
                status_code=200,
                file_path=view["file"],
                line_number=view["line"],
            )
            self.endpoints.append(endpoint)

    def _get_viewset_parameters(self, action: str) -> List[EndpointParameter]:
        """Get parameters for a ViewSet action"""
        parameters = []

        # Actions that need an ID parameter
        if action in ["retrieve", "update", "partial_update", "destroy"]:
            parameters.append(EndpointParameter(name="id", param_type="path", data_type="int", required=True))

        # List action typically has pagination parameters
        if action == "list":
            parameters.extend(
                [
                    EndpointParameter(name="page", param_type="query", data_type="int", required=False),
                    EndpointParameter(name="page_size", param_type="query", data_type="int", required=False),
                ]
            )

        return parameters
