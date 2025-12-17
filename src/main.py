"""
Main CLI Application
Entry point for the Doc Agent CLI and optional FastAPI service
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .analyzers import detect_framework, get_analyzer
from .doc_manager import DocumentationManager
from .git_helper import GitHelper
from .groq_service import GroqService

app = typer.Typer(
    name="doc-agent",
    help="AI-powered API documentation generator for FastAPI applications",
    add_completion=False,
)

console = Console()


@app.command()
def generate(
    path: str = typer.Option(".", "--path", "-p", help="Path to API project directory"),
    output: str = typer.Option("./docs/API.md", "--output", "-o", help="Output path for documentation file"),
    project_name: str = typer.Option("API", "--name", "-n", help="Project name for documentation"),
    framework: Optional[str] = typer.Option(
        None, "--framework", "-f", help="Framework: 'fastapi' or 'django' (auto-detected if not specified)"
    ),
    groq_api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        "-k",
        help="Groq API key (or set GROQ_API_KEY env var)",
        envvar="GROQ_API_KEY",
    ),
    groq_model: str = typer.Option("llama-3.3-70b-versatile", "--model", "-m", help="Groq model to use"),
    save_analysis: bool = typer.Option(False, "--save-analysis", help="Save endpoint analysis to JSON file"),
    auto_commit: bool = typer.Option(False, "--auto-commit", help="Automatically commit generated documentation"),
    agentic: bool = typer.Option(False, "--agentic", help="Enable agentic review and self-correction loop"),
):
    """
    Generate or update API documentation for FastAPI or Django projects
    """

    console.print("\n[bold cyan]🤖 Doc Agent - AI API Documentation Generator[/bold cyan]\n")

    # Validate paths
    project_path = Path(path).resolve()
    if not project_path.exists():
        console.print(f"[red]❌ Error: Project path does not exist: {project_path}[/red]")
        raise typer.Exit(1)

    # Validate API key
    if not groq_api_key:
        console.print(
            "[red]❌ Error: GROQ_API_KEY not set. Please provide via --api-key or environment variable.[/red]"
        )
        raise typer.Exit(1)

    try:
        # Detect framework if not specified
        if framework is None:
            detected = detect_framework(project_path)
            console.print(f"[dim]🔍 Detected framework: {detected}[/dim]")
            framework = detected
        else:
            console.print(f"[dim]📦 Using framework: {framework}[/dim]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Step 1: Analyze code
            task = progress.add_task(f"Analyzing {framework.title()} code...", total=None)
            analyzer = get_analyzer(framework, str(project_path))
            endpoints = analyzer.analyze()
            progress.update(task, completed=True)

            if not endpoints:
                console.print("[yellow]⚠️  No FastAPI endpoints found in the project.[/yellow]")
                raise typer.Exit(0)

            console.print(f"[green]✓[/green] Found {len(endpoints)} endpoint(s)")

            # Save analysis if requested
            if save_analysis:
                analysis_file = Path(output).parent / "endpoints_analysis.json"
                analyzer.save_analysis(str(analysis_file))
                console.print(f"[dim]  Analysis saved to: {analysis_file}[/dim]")

            # Step 2: Initialize Groq service
            task = progress.add_task("Initializing Groq AI service...", total=None)
            groq_service = GroqService(api_key=groq_api_key, model=groq_model)
            progress.update(task, completed=True)
            console.print(f"[green]✓[/green] Using model: {groq_model}")

            # Step 3: Generate/update documentation
            task = progress.add_task("Generating documentation with AI...", total=None)
            doc_manager = DocumentationManager(output, groq_service)
            doc_path = doc_manager.generate_or_update(endpoints, project_name, agentic=agentic)
            progress.update(task, completed=True)
            console.print(f"[green]✓[/green] Documentation ready: {doc_path}")

        # Step 4: Auto-commit if requested
        if auto_commit:
            git_helper = GitHelper(str(project_path))
            if git_helper.is_git_repository():
                git_helper.commit_documentation([output], "docs: Update API documentation [doc-agent]")
                console.print("[green]✓[/green] Changes committed to Git")
            else:
                console.print("[yellow]⚠️  Not a Git repository, skipping auto-commit[/yellow]")

        console.print("\n[bold green]🎉 Documentation generation complete![/bold green]\n")

    except Exception as e:
        console.print(f"\n[red]❌ Error: {str(e)}[/red]\n")
        raise typer.Exit(1)


@app.command()
def analyze(
    path: str = typer.Option(".", "--path", "-p", help="Path to API project directory"),
    output: str = typer.Option(
        "./endpoints_analysis.json",
        "--output",
        "-o",
        help="Output path for analysis JSON file",
    ),
    framework: Optional[str] = typer.Option(
        None, "--framework", "-f", help="Framework: 'fastapi' or 'django' (auto-detected if not specified)"
    ),
):
    """
    Analyze API code and output endpoint information (no AI generation)
    """

    console.print("\n[bold cyan]🔍 Analyzing API Endpoints[/bold cyan]\n")

    project_path = Path(path).resolve()
    if not project_path.exists():
        console.print(f"[red]❌ Error: Project path does not exist: {project_path}[/red]")
        raise typer.Exit(1)

    try:
        # Detect framework if not specified
        if framework is None:
            detected = detect_framework(project_path)
            console.print(f"[dim]🔍 Detected framework: {detected}[/dim]")
            framework = detected

        analyzer = get_analyzer(framework, str(project_path))
        endpoints = analyzer.analyze()

        if not endpoints:
            console.print("[yellow]⚠️  No FastAPI endpoints found.[/yellow]")
            raise typer.Exit(0)

        analyzer.save_analysis(output)

        console.print(f"[green]✓[/green] Found {len(endpoints)} endpoint(s)")
        console.print(f"[green]✓[/green] Analysis saved: {output}\n")

        # Print summary
        console.print("[bold]Endpoints:[/bold]")
        for ep in endpoints:
            console.print(f"  • {ep.method:6} {ep.path:30} → {ep.function_name}")

        console.print()

    except Exception as e:
        console.print(f"\n[red]❌ Error: {str(e)}[/red]\n")
        raise typer.Exit(1)


@app.command()
def version():
    """Show version information"""
    from . import __version__

    console.print(f"[bold]Doc Agent[/bold] version {__version__}")


def main():
    """Main entry point"""
    app()


if __name__ == "__main__":
    main()
