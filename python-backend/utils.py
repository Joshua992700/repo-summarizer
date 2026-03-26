"""
Utility functions for file processing and tech stack detection.
"""

from typing import Dict, List, Optional, Tuple
import re


# Maximum lines to include per file for summarization
MAX_LINES_PER_FILE = 200

# App type detection patterns - maps keywords to app categories
APP_TYPE_PATTERNS: Dict[str, Dict[str, any]] = {
    "Booking/Reservation App": {
        "keywords": [
            "booking",
            "reservation",
            "appointment",
            "schedule",
            "slot",
            "turf",
            "venue",
            "court",
            "ground",
            "field",
            "stadium",
            "hotel",
            "room",
            "check-in",
            "checkout",
            "availability",
            "calendar",
            "timeslot",
            "book now",
            "reserve",
        ],
        "file_patterns": ["booking", "reservation", "appointment", "schedule"],
    },
    "E-commerce/Shopping App": {
        "keywords": [
            "cart",
            "checkout",
            "payment",
            "order",
            "product",
            "shop",
            "store",
            "price",
            "inventory",
            "catalog",
            "wishlist",
            "add to cart",
            "buy now",
            "shipping",
            "discount",
            "coupon",
        ],
        "file_patterns": ["cart", "product", "checkout", "order", "shop"],
    },
    "Social Media/Networking App": {
        "keywords": [
            "post",
            "feed",
            "follow",
            "like",
            "comment",
            "share",
            "profile",
            "friend",
            "message",
            "notification",
            "timeline",
            "social",
            "community",
            "network",
        ],
        "file_patterns": ["feed", "post", "profile", "social", "follow"],
    },
    "Chat/Messaging App": {
        "keywords": [
            "chat",
            "message",
            "conversation",
            "inbox",
            "send message",
            "real-time",
            "websocket",
            "notification",
            "typing",
        ],
        "file_patterns": ["chat", "message", "conversation", "inbox"],
    },
    "Authentication/User Management": {
        "keywords": [
            "login",
            "signup",
            "register",
            "auth",
            "password",
            "user",
            "session",
            "token",
            "oauth",
            "sso",
            "forgot password",
        ],
        "file_patterns": ["auth", "login", "signup", "user"],
    },
    "Dashboard/Analytics App": {
        "keywords": [
            "dashboard",
            "analytics",
            "metrics",
            "chart",
            "graph",
            "statistics",
            "report",
            "visualization",
            "monitor",
        ],
        "file_patterns": ["dashboard", "analytics", "chart", "report"],
    },
    "Blog/CMS": {
        "keywords": [
            "blog",
            "post",
            "article",
            "content",
            "cms",
            "editor",
            "publish",
            "draft",
            "category",
            "tag",
            "author",
        ],
        "file_patterns": ["blog", "post", "article", "editor"],
    },
    "Task/Project Management": {
        "keywords": [
            "task",
            "project",
            "todo",
            "kanban",
            "board",
            "sprint",
            "milestone",
            "deadline",
            "assign",
            "progress",
            "workflow",
        ],
        "file_patterns": ["task", "project", "todo", "kanban", "board"],
    },
    "Video/Media Streaming": {
        "keywords": [
            "video",
            "stream",
            "player",
            "media",
            "watch",
            "playlist",
            "channel",
            "subscribe",
            "upload",
            "thumbnail",
        ],
        "file_patterns": ["video", "player", "stream", "media"],
    },
    "Food Delivery/Restaurant App": {
        "keywords": [
            "restaurant",
            "menu",
            "food",
            "delivery",
            "order food",
            "cuisine",
            "dish",
            "table",
            "dine",
            "takeaway",
        ],
        "file_patterns": ["restaurant", "menu", "food", "delivery"],
    },
    "Fitness/Health App": {
        "keywords": [
            "workout",
            "fitness",
            "exercise",
            "health",
            "gym",
            "training",
            "calories",
            "diet",
            "nutrition",
            "tracker",
        ],
        "file_patterns": ["workout", "fitness", "health", "exercise"],
    },
    "Educational/Learning Platform": {
        "keywords": [
            "course",
            "lesson",
            "learn",
            "education",
            "quiz",
            "exam",
            "student",
            "teacher",
            "classroom",
            "assignment",
            "grade",
        ],
        "file_patterns": ["course", "lesson", "quiz", "student", "learn"],
    },
    "Real Estate/Property App": {
        "keywords": [
            "property",
            "real estate",
            "listing",
            "rent",
            "buy",
            "sell",
            "house",
            "apartment",
            "agent",
            "mortgage",
        ],
        "file_patterns": ["property", "listing", "real-estate", "house"],
    },
    "Finance/Banking App": {
        "keywords": [
            "transaction",
            "balance",
            "account",
            "transfer",
            "bank",
            "wallet",
            "payment",
            "invoice",
            "expense",
            "budget",
        ],
        "file_patterns": ["transaction", "account", "wallet", "payment"],
    },
    "Job/Recruitment Portal": {
        "keywords": [
            "job",
            "career",
            "resume",
            "apply",
            "candidate",
            "employer",
            "interview",
            "hire",
            "vacancy",
            "recruitment",
        ],
        "file_patterns": ["job", "career", "resume", "candidate"],
    },
}

# Important files that should be prioritized in summarization
PRIORITY_FILES = [
    "README.md",
    "readme.md",
    "README.rst",
    "README",
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "Gemfile",
    "composer.json",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    ".env.example",
    "Makefile",
    "main.py",
    "main.go",
    "main.rs",
    "index.js",
    "index.ts",
    "app.py",
    "server.py",
    "app.js",
    "server.js",
]

# Tech stack detection patterns
TECH_STACK_PATTERNS: Dict[str, Dict[str, any]] = {
    # Languages
    "Python": {
        "files": ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"],
        "extensions": [".py"],
    },
    "JavaScript": {
        "files": ["package.json"],
        "extensions": [".js", ".jsx"],
    },
    "TypeScript": {
        "files": ["tsconfig.json"],
        "extensions": [".ts", ".tsx"],
    },
    "Go": {
        "files": ["go.mod", "go.sum"],
        "extensions": [".go"],
    },
    "Rust": {
        "files": ["Cargo.toml"],
        "extensions": [".rs"],
    },
    "Java": {
        "files": ["pom.xml", "build.gradle"],
        "extensions": [".java"],
    },
    "Ruby": {
        "files": ["Gemfile"],
        "extensions": [".rb"],
    },
    "PHP": {
        "files": ["composer.json"],
        "extensions": [".php"],
    },
    "C#": {
        "files": ["*.csproj"],
        "extensions": [".cs"],
    },
    # Frameworks
    "React": {
        "content_patterns": [r"from ['\"]react['\"]", r"import React"],
        "files": [],
    },
    "Vue.js": {
        "content_patterns": [r"from ['\"]vue['\"]", r"<template>"],
        "extensions": [".vue"],
    },
    "Next.js": {
        "files": ["next.config.js", "next.config.mjs"],
        "content_patterns": [r"from ['\"]next"],
    },
    "FastAPI": {
        "content_patterns": [r"from fastapi", r"import fastapi"],
    },
    "Flask": {
        "content_patterns": [r"from flask", r"import flask"],
    },
    "Django": {
        "files": ["manage.py"],
        "content_patterns": [r"from django", r"import django"],
    },
    "Express": {
        "content_patterns": [r"require\(['\"]express['\"]", r"from ['\"]express['\"]"],
    },
    "Gin": {
        "content_patterns": [r"github.com/gin-gonic/gin"],
    },
    # Tools
    "Docker": {
        "files": ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"],
    },
    "Kubernetes": {
        "files": ["k8s/", "kubernetes/"],
        "content_patterns": [r"kind:\s*Deployment", r"apiVersion:\s*apps/v1"],
    },
    "GitHub Actions": {
        "files": [".github/workflows/"],
    },
    "Jest": {
        "files": ["jest.config.js"],
        "content_patterns": [r"from ['\"]jest['\"]"],
    },
    "Pytest": {
        "content_patterns": [r"import pytest", r"from pytest"],
    },
    "Tailwind CSS": {
        "files": ["tailwind.config.js", "tailwind.config.ts"],
    },
}


def truncate_file_content(content: str, max_lines: int = MAX_LINES_PER_FILE) -> str:
    """Truncate file content to a maximum number of lines."""
    lines = content.split("\n")
    if len(lines) <= max_lines:
        return content

    truncated = "\n".join(lines[:max_lines])
    return truncated + f"\n\n... [truncated - {len(lines) - max_lines} more lines]"


def is_priority_file(path: str) -> bool:
    """Check if a file should be prioritized in summarization."""
    filename = path.split("/")[-1]
    return filename in PRIORITY_FILES or path in PRIORITY_FILES


def sort_files_by_priority(files: List[Dict]) -> List[Dict]:
    """Sort files with priority files first."""
    priority = []
    regular = []

    for file in files:
        if is_priority_file(file.get("path", "")):
            priority.append(file)
        else:
            regular.append(file)

    return priority + regular


def detect_tech_stack(files: List[Dict]) -> Dict[str, List[str]]:
    """
    Detect the tech stack from repository files.

    Returns:
        Dict with keys: 'languages', 'frameworks', 'tools'
    """
    detected = {
        "languages": set(),
        "frameworks": set(),
        "tools": set(),
    }

    # Collect all file paths and content for analysis
    file_paths = [f.get("path", "") for f in files]
    all_content = "\n".join(
        f.get("content", "")[:5000] for f in files
    )  # Limit content per file

    for tech, patterns in TECH_STACK_PATTERNS.items():
        found = False

        # Check for specific files
        if "files" in patterns:
            for pattern_file in patterns.get("files", []):
                for path in file_paths:
                    if pattern_file in path:
                        found = True
                        break
                if found:
                    break

        # Check for file extensions
        if not found and "extensions" in patterns:
            for ext in patterns.get("extensions", []):
                if any(path.endswith(ext) for path in file_paths):
                    found = True
                    break

        # Check for content patterns
        if not found and "content_patterns" in patterns:
            for pattern in patterns.get("content_patterns", []):
                if re.search(pattern, all_content, re.IGNORECASE):
                    found = True
                    break

        if found:
            # Categorize the technology
            if tech in [
                "Python",
                "JavaScript",
                "TypeScript",
                "Go",
                "Rust",
                "Java",
                "Ruby",
                "PHP",
                "C#",
            ]:
                detected["languages"].add(tech)
            elif tech in [
                "Docker",
                "Kubernetes",
                "GitHub Actions",
                "Jest",
                "Pytest",
                "Tailwind CSS",
            ]:
                detected["tools"].add(tech)
            else:
                detected["frameworks"].add(tech)

    return {k: sorted(list(v)) for k, v in detected.items()}


def extract_dependencies(files: List[Dict]) -> Dict[str, List[str]]:
    """Extract dependencies from package manager files."""
    dependencies = {}

    for file in files:
        path = file.get("path", "")
        content = file.get("content", "")

        # Python requirements.txt
        if path.endswith("requirements.txt"):
            deps = []
            for line in content.split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    # Extract package name (before ==, >=, etc.)
                    pkg = re.split(r"[=<>!~\[]", line)[0].strip()
                    if pkg:
                        deps.append(pkg)
            if deps:
                dependencies["python"] = deps[:20]  # Limit to 20

        # Node.js package.json
        if path.endswith("package.json"):
            try:
                import json

                pkg = json.loads(content)
                node_deps = []
                for key in ["dependencies", "devDependencies"]:
                    if key in pkg:
                        node_deps.extend(list(pkg[key].keys())[:10])
                if node_deps:
                    dependencies["node"] = node_deps[:20]
            except:
                pass

        # Go go.mod
        if path.endswith("go.mod"):
            deps = []
            in_require = False
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("require ("):
                    in_require = True
                    continue
                if in_require and line == ")":
                    in_require = False
                    continue
                if in_require or line.startswith("require "):
                    parts = line.replace("require ", "").split()
                    if parts:
                        deps.append(parts[0])
            if deps:
                dependencies["go"] = deps[:20]

    return dependencies


def estimate_project_size(files: List[Dict]) -> Dict[str, int]:
    """Estimate project size metrics."""
    total_lines = 0
    total_files = len(files)

    extensions_count: Dict[str, int] = {}

    for file in files:
        content = file.get("content", "")
        total_lines += content.count("\n") + 1

        path = file.get("path", "")
        if "." in path:
            ext = "." + path.split(".")[-1]
            extensions_count[ext] = extensions_count.get(ext, 0) + 1

    return {
        "total_files": total_files,
        "total_lines": total_lines,
        "file_types": extensions_count,
    }


def extract_readme_content(files: List[Dict]) -> Optional[str]:
    """Extract README content from files."""
    readme_names = ["README.md", "readme.md", "README.rst", "README.txt", "README"]

    for file in files:
        path = file.get("path", "")
        filename = path.split("/")[-1]
        if filename in readme_names:
            return file.get("content", "")

    return None


def chunk_content(content: str, max_chars: int = 10000) -> List[str]:
    """Split content into chunks of maximum size."""
    if len(content) <= max_chars:
        return [content]

    chunks = []
    current_chunk = ""

    for line in content.split("\n"):
        if len(current_chunk) + len(line) + 1 > max_chars:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = line
        else:
            current_chunk += ("\n" if current_chunk else "") + line

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def format_file_tree(files: List[Dict], max_depth: int = 3) -> str:
    """Generate a simple file tree representation."""
    paths = sorted([f.get("path", "") for f in files])

    # Build tree structure
    tree_lines = []
    prev_parts = []

    for path in paths[:50]:  # Limit to 50 files for display
        parts = path.split("/")

        # Find common prefix with previous path
        common = 0
        for i, (a, b) in enumerate(zip(prev_parts, parts)):
            if a == b:
                common = i + 1
            else:
                break

        # Add new path components
        for i, part in enumerate(parts[common:], start=common):
            if i < max_depth:
                indent = "  " * i
                prefix = "├── " if i > 0 else ""
                tree_lines.append(f"{indent}{prefix}{part}")

        prev_parts = parts

    if len(paths) > 50:
        tree_lines.append(f"\n... and {len(paths) - 50} more files")

    return "\n".join(tree_lines)


def detect_app_type(
    files: List[Dict], readme_content: Optional[str] = None
) -> Dict[str, any]:
    """
    Detect the type/purpose of the application from code and README.

    Returns:
        Dict with 'app_type', 'confidence', and 'detected_keywords'
    """
    # Collect all searchable content
    file_paths = [f.get("path", "").lower() for f in files]

    # Get content from key files (components, pages, etc.)
    code_content = ""
    for file in files:
        path = file.get("path", "").lower()
        # Focus on meaningful files
        if any(
            x in path
            for x in ["component", "page", "screen", "view", "route", "api", "service"]
        ):
            code_content += " " + file.get("content", "")[:3000]

    # Add README content
    if readme_content:
        code_content = readme_content + " " + code_content

    code_content = code_content.lower()

    # Score each app type
    scores: Dict[str, Dict] = {}

    for app_type, patterns in APP_TYPE_PATTERNS.items():
        score = 0
        found_keywords = []

        # Check keywords in content
        for keyword in patterns.get("keywords", []):
            keyword_lower = keyword.lower()
            count = code_content.count(keyword_lower)
            if count > 0:
                score += min(count, 5)  # Cap contribution per keyword
                found_keywords.append(keyword)

        # Check file path patterns
        for pattern in patterns.get("file_patterns", []):
            pattern_lower = pattern.lower()
            matches = sum(1 for p in file_paths if pattern_lower in p)
            if matches > 0:
                score += matches * 3  # File patterns are strong indicators
                if pattern not in found_keywords:
                    found_keywords.append(f"file:{pattern}")

        if score > 0:
            scores[app_type] = {
                "score": score,
                "keywords": found_keywords[:5],
            }

    # Find the best match
    if not scores:
        return {
            "app_type": None,
            "confidence": 0.0,
            "detected_keywords": [],
        }

    best_match = max(scores.items(), key=lambda x: x[1]["score"])
    app_type = best_match[0]
    details = best_match[1]

    # Calculate confidence (normalize score)
    max_possible = 30  # Rough estimate of max score
    confidence = min(details["score"] / max_possible, 1.0)

    return {
        "app_type": app_type,
        "confidence": confidence,
        "detected_keywords": details["keywords"],
        "all_matches": sorted(
            [(k, v["score"]) for k, v in scores.items()],
            key=lambda x: x[1],
            reverse=True,
        )[:3],
    }


def extract_project_description(
    files: List[Dict], readme_content: Optional[str] = None
) -> Dict[str, str]:
    """
    Extract a meaningful project description from README and package files.

    Returns:
        Dict with 'description', 'tagline', and 'source'
    """
    result = {
        "description": "",
        "tagline": "",
        "source": "none",
    }

    # Try package.json description first (often concise)
    for file in files:
        path = file.get("path", "")
        content = file.get("content", "")

        if path.endswith("package.json"):
            try:
                import json

                pkg = json.loads(content)
                if pkg.get("description"):
                    result["description"] = pkg["description"]
                    result["source"] = "package.json"
                if pkg.get("name"):
                    result["tagline"] = pkg["name"]
            except:
                pass

    # Parse README for better description
    if readme_content:
        lines = readme_content.split("\n")

        # Strategy 1: Look for description after title
        title_found = False
        for i, line in enumerate(lines[:40]):
            line = line.strip()

            # Skip badges and images
            if line.startswith("!") or line.startswith("[!["):
                continue

            # Found title
            if line.startswith("# "):
                title_found = True
                if not result["tagline"]:
                    result["tagline"] = line[2:].strip()
                continue

            # First substantial paragraph after title
            if title_found and line and len(line) > 30:
                # Skip common non-description lines
                skip_patterns = [
                    r"^#{2,}",  # Sub-headers
                    r"^\[",  # Links
                    r"^>",  # Blockquotes that are not descriptions
                    r"^```",  # Code blocks
                    r"^\|",  # Tables
                    r"^-{3,}",  # Horizontal rules
                    r"open.*localhost",  # Dev instructions
                    r"npm|yarn|pnpm",  # Install instructions
                ]

                if not any(re.match(p, line, re.IGNORECASE) for p in skip_patterns):
                    # This looks like a description
                    desc = line[:500]
                    if len(desc) > len(result.get("description", "")):
                        result["description"] = desc
                        result["source"] = "README.md"
                    break

        # Strategy 2: Look for "About" or "Description" section
        for i, line in enumerate(lines):
            if re.match(
                r"^##\s*(about|description|overview|what is|introduction)",
                line,
                re.IGNORECASE,
            ):
                # Get content after this header
                for j in range(i + 1, min(i + 10, len(lines))):
                    content_line = lines[j].strip()
                    if (
                        content_line
                        and not content_line.startswith("#")
                        and len(content_line) > 30
                    ):
                        if len(content_line) > len(result.get("description", "")):
                            result["description"] = content_line[:500]
                            result["source"] = "README.md (About section)"
                        break
                break

    return result
