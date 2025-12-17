"""
Framework Detector Module
Auto-detects the web framework used in a project
"""

import re
from pathlib import Path


def detect_framework(project_path: Path) -> str:
    """
    Auto-detect the web framework used in the project

    Args:
        project_path: Path to the project directory

    Returns:
        Framework name: 'fastapi', 'django', or 'unknown'
    """

    # Check for Django-specific files
    if _is_django_project(project_path):
        return "django"

    # Check for FastAPI
    if _is_fastapi_project(project_path):
        return "fastapi"

    # Default to FastAPI for backward compatibility
    return "fastapi"


def _is_django_project(project_path: Path) -> bool:
    """Check if project is a Django project"""

    # Check for manage.py
    if (project_path / "manage.py").exists():
        return True

    # Check for settings.py in common locations
    settings_patterns = [
        "**/settings.py",
        "**/settings/*.py",
    ]

    for pattern in settings_patterns:
        if list(project_path.glob(pattern)):
            return True

    # Check for Django imports in Python files
    python_files = list(project_path.glob("**/*.py"))[:20]  # Sample first 20 files
    django_import_pattern = re.compile(r'^\s*from django|^\s*import django', re.MULTILINE)

    for py_file in python_files:
        try:
            content = py_file.read_text(encoding='utf-8')
            if django_import_pattern.search(content):
                return True
        except Exception:
            continue

    return False


def _is_fastapi_project(project_path: Path) -> bool:
    """Check if project is a FastAPI project"""

    # Check for FastAPI imports in Python files
    python_files = list(project_path.glob("**/*.py"))[:20]  # Sample first 20 files
    fastapi_import_pattern = re.compile(r'^\s*from fastapi|^\s*import fastapi', re.MULTILINE)

    for py_file in python_files:
        try:
            content = py_file.read_text(encoding='utf-8')
            if fastapi_import_pattern.search(content):
                return True
        except Exception:
            continue

    return False


def get_analyzer(framework: str, project_path: str):
    """
    Get the appropriate analyzer for the detected framework

    Args:
        framework: Framework name ('fastapi', 'django')
        project_path: Path to the project

    Returns:
        Analyzer instance

    Raises:
        ValueError: If framework is not supported
    """

    if framework == "fastapi":
        from .fastapi_analyzer import FastAPIAnalyzer

        return FastAPIAnalyzer(project_path)
    elif framework == "django":
        from .django_analyzer import DjangoAnalyzer

        return DjangoAnalyzer(project_path)
    else:
        raise ValueError(f"Unsupported framework: {framework}. Supported: fastapi, django")
