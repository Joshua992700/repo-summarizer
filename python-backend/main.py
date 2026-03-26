import sys
import os

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv not installed, rely on system env vars

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.tree import Tree
from rich.markdown import Markdown
from rich import box

from api_client import create_client, GoParserClient
from summarizer import create_summarizer, RepoSummary


console = Console()


def print_banner():
    banner = """
╦═╗┌─┐┌─┐┌─┐  ╔═╗┬ ┬┌┬┐┌┬┐┌─┐┬─┐┬┌─┐┌─┐┬─┐
╠╦╝├┤ ├─┘│ │  ╚═╗│ │││││││├─┤├┬┘│┌─┘├┤ ├┬┘
╩╚═└─┘┴  └─┘  ╚═╝└─┘┴ ┴┴ ┴┴ ┴┴└─┴└─┘└─┘┴└─
    """
    console.print(banner, style="bold cyan")
    console.print("  Analyze GitHub repos in seconds!\n", style="dim")


def validate_github_url(url: str) -> bool:
    url = url.strip()
    valid_prefixes = [
        "https://github.com/",
        "http://github.com/",
        "https://www.github.com/",
        "git@github.com:",
    ]
    return any(url.startswith(prefix) for prefix in valid_prefixes)


def print_summary(summary: RepoSummary):
    # Header
    console.print()
    console.print(
        Panel(
            f"[bold white]{summary.repo_name}[/bold white]",
            title="Repository Analysis",
            border_style="cyan",
        )
    )

    # App Type (prominent display if detected)
    if summary.app_type:
        console.print()
        console.print(
            f"[bold magenta]🎯 App Type:[/bold magenta] [bold white]{summary.app_type}[/bold white]"
        )

    # Description
    if summary.description:
        console.print()
        console.print("[bold]Description:[/bold]")
        console.print(f"  {summary.description}", style="white")

    # Purpose
    if summary.purpose:
        console.print()
        console.print("[bold]What it is:[/bold]")
        console.print(f"  {summary.purpose}", style="white")

    # Tech Stack Table
    console.print()
    tech_table = Table(title="Tech Stack", box=box.ROUNDED, show_header=True)
    tech_table.add_column("Category", style="cyan")
    tech_table.add_column("Technologies", style="green")

    if summary.tech_stack.get("languages"):
        tech_table.add_row("Languages", ", ".join(summary.tech_stack["languages"]))
    if summary.tech_stack.get("frameworks"):
        tech_table.add_row("Frameworks", ", ".join(summary.tech_stack["frameworks"]))
    if summary.tech_stack.get("tools"):
        tech_table.add_row("Tools", ", ".join(summary.tech_stack["tools"]))

    if tech_table.row_count > 0:
        console.print(tech_table)

    # Dependencies
    if summary.dependencies:
        console.print()
        dep_table = Table(title="Key Dependencies", box=box.ROUNDED)
        dep_table.add_column("Package Manager", style="cyan")
        dep_table.add_column("Packages", style="yellow")

        for pkg_manager, deps in summary.dependencies.items():
            dep_table.add_row(pkg_manager.capitalize(), ", ".join(deps[:10]))

        console.print(dep_table)

    # Key Features
    if summary.key_features:
        console.print()
        console.print("[bold]Key Features:[/bold]")
        for feature in summary.key_features:
            console.print(f"  • {feature}", style="green")

    # Project Size
    console.print()
    size_table = Table(title="Project Metrics", box=box.ROUNDED)
    size_table.add_column("Metric", style="cyan")
    size_table.add_column("Value", style="white")

    size_table.add_row("Total Files", str(summary.project_size.get("total_files", 0)))
    size_table.add_row("Total Lines", f"{summary.project_size.get('total_lines', 0):,}")

    # Top file types
    file_types = summary.project_size.get("file_types", {})
    if file_types:
        sorted_types = sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:5]
        types_str = ", ".join(f"{ext}({count})" for ext, count in sorted_types)
        size_table.add_row("File Types", types_str)

    console.print(size_table)

    # Confidence indicator
    console.print()
    confidence = summary.confidence_score
    confidence_bar = "█" * int(confidence * 10) + "░" * (10 - int(confidence * 10))
    confidence_color = (
        "green" if confidence > 0.7 else "yellow" if confidence > 0.5 else "red"
    )

    console.print(
        f"[bold]Confidence:[/bold] [{confidence_color}]{confidence_bar}[/{confidence_color}] "
        f"{confidence:.0%} ({summary.summary_method})"
    )

    # File Tree (collapsed by default)
    console.print()
    console.print("[bold]File Structure:[/bold] [dim](showing top files)[/dim]")
    console.print(
        Panel(
            summary.file_tree[:1500]
            if len(summary.file_tree) > 1500
            else summary.file_tree,
            border_style="dim",
        )
    )


def main():
    print_banner()

    # Get GitHub URL from user
    try:
        if len(sys.argv) > 1:
            github_url = sys.argv[1]
        else:
            github_url = console.input("[bold cyan]Paste GitHub repo URL:[/bold cyan] ")
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Cancelled.[/yellow]")
        sys.exit(0)

    # Validate URL
    if not validate_github_url(github_url):
        console.print(
            "[red]Error:[/red] Invalid GitHub URL. Please provide a valid GitHub repository URL."
        )
        console.print("[dim]Example: https://github.com/username/repo[/dim]")
        sys.exit(1)

    # Initialize clients
    client = create_client()
    summarizer = create_summarizer(use_ai=True)

    # Show AI status
    if summarizer.ai_status == "groq":
        console.print("[dim]Using Groq AI (llama-3.3-70b)[/dim]")
    elif summarizer.ai_status == "openai":
        console.print("[dim]Using OpenAI[/dim]")
    else:
        console.print(
            "[dim]Using heuristic analysis (set GROQ_API_KEY for better results)[/dim]"
        )
    console.print()

    # Check if Go service is running
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Step 1: Check service health
        task = progress.add_task("Checking Go parser service...", total=None)

        if not client.health_check():
            progress.stop()
            console.print()
            console.print("[red]Error:[/red] Go parser service is not running!")
            console.print()
            console.print("[yellow]To start the service:[/yellow]")
            console.print("  cd go-parser")
            console.print("  go mod tidy")
            console.print("  go run main.go")
            console.print()
            sys.exit(1)

        progress.update(task, description="Go parser service is running!")

        # Step 2: Parse repository
        progress.update(task, description=f"Cloning and parsing repository...")

        try:
            repo_data = client.parse_repo(github_url)
        except ConnectionError as e:
            progress.stop()
            console.print(f"\n[red]Connection Error:[/red] {e}")
            sys.exit(1)
        except TimeoutError as e:
            progress.stop()
            console.print(f"\n[red]Timeout:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            progress.stop()
            console.print(f"\n[red]Error:[/red] {e}")
            sys.exit(1)

        if repo_data.error:
            progress.stop()
            console.print(f"\n[red]Error parsing repository:[/red] {repo_data.error}")

            if "authentication required" in repo_data.error.lower():
                console.print("[yellow]This might be a private repository.[/yellow]")
            elif "not found" in repo_data.error.lower():
                console.print(
                    "[yellow]Repository not found. Check the URL and try again.[/yellow]"
                )

            sys.exit(1)

        if not repo_data.files:
            progress.stop()
            console.print("\n[yellow]Warning:[/yellow] No files found in repository.")
            console.print(
                "[dim]The repository might be empty or contain only binary files.[/dim]"
            )
            sys.exit(1)

        progress.update(task, description=f"Parsed {len(repo_data.files)} files!")

        # Step 3: Generate summary
        progress.update(task, description="Generating summary...")

        summary = summarizer.summarize(repo_data.repo_name, repo_data.files)

        progress.update(task, description="Summary complete!")

    # Print the summary
    print_summary(summary)

    console.print()
    console.print("[dim]Generated by Repo Summarizer - Built for Developers![/dim]")
    console.print()


if __name__ == "__main__":
    main()
