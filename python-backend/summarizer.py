"""
Summarization logic for repository analysis.
Supports AI (Groq, OpenAI) and improved heuristic-based summarization.

Production-ready with proper error handling and domain detection.
"""

import os
import re
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class RepoSummary:
    """Represents a repository summary."""

    repo_name: str
    description: str
    purpose: str
    tech_stack: Dict[str, List[str]]
    dependencies: Dict[str, List[str]]
    project_size: Dict[str, int]
    key_features: List[str]
    file_tree: str
    confidence_score: float  # 0.0 to 1.0
    summary_method: str  # "groq", "openai", or "heuristic"
    app_type: Optional[str] = None  # Detected app category


class Summarizer:
    """Repository summarizer with AI (Groq/OpenAI) and heuristic fallback."""

    def __init__(self, use_ai: bool = True):
        """
        Initialize the summarizer.

        Args:
            use_ai: Whether to attempt AI summarization
        """
        self.groq_client = None
        self.openai_client = None
        self.use_groq = False
        self.use_openai = False
        self.ai_status = "none"

        # Try Groq first (faster and has free tier)
        groq_key = os.getenv("GROQ_API_KEY")
        if use_ai and groq_key:
            try:
                from groq import Groq

                self.groq_client = Groq(api_key=groq_key)
                self.use_groq = True
                self.ai_status = "groq"
            except ImportError:
                pass
            except Exception as e:
                print(f"Groq init error: {e}")

        # Fallback to OpenAI
        openai_key = os.getenv("OPENAI_API_KEY")
        if use_ai and not self.use_groq and openai_key:
            try:
                from openai import OpenAI

                self.openai_client = OpenAI(api_key=openai_key)
                self.use_openai = True
                self.ai_status = "openai"
            except ImportError:
                pass
            except Exception as e:
                print(f"OpenAI init error: {e}")

    def summarize(self, repo_name: str, files: List[Dict]) -> RepoSummary:
        """
        Generate a summary for the repository.

        Args:
            repo_name: Name of the repository
            files: List of file dicts with 'path' and 'content' keys

        Returns:
            RepoSummary object
        """
        from utils import (
            detect_tech_stack,
            extract_dependencies,
            estimate_project_size,
            format_file_tree,
            extract_readme_content,
        )

        # Extract basic info
        tech_stack = detect_tech_stack(files)
        dependencies = extract_dependencies(files)
        project_size = estimate_project_size(files)
        file_tree = format_file_tree(files)
        readme_content = extract_readme_content(files)

        # Build rich code context
        code_context = self._build_code_context(files, readme_content)

        # Try Groq AI first
        if self.use_groq:
            try:
                ai_summary = self._groq_summarize(repo_name, code_context, tech_stack)
                if ai_summary and ai_summary.get("app_type"):
                    return RepoSummary(
                        repo_name=repo_name,
                        description=ai_summary.get("description", ""),
                        purpose=ai_summary.get("purpose", ""),
                        tech_stack=tech_stack,
                        dependencies=dependencies,
                        project_size=project_size,
                        key_features=ai_summary.get("key_features", []),
                        file_tree=file_tree,
                        confidence_score=0.92,
                        summary_method="groq",
                        app_type=ai_summary.get("app_type"),
                    )
            except Exception as e:
                print(f"Groq error: {e}")

        # Try OpenAI
        if self.use_openai:
            try:
                ai_summary = self._openai_summarize(repo_name, code_context, tech_stack)
                if ai_summary and ai_summary.get("app_type"):
                    return RepoSummary(
                        repo_name=repo_name,
                        description=ai_summary.get("description", ""),
                        purpose=ai_summary.get("purpose", ""),
                        tech_stack=tech_stack,
                        dependencies=dependencies,
                        project_size=project_size,
                        key_features=ai_summary.get("key_features", []),
                        file_tree=file_tree,
                        confidence_score=0.90,
                        summary_method="openai",
                        app_type=ai_summary.get("app_type"),
                    )
            except Exception as e:
                print(f"OpenAI error: {e}")

        # Fallback to heuristic
        heuristic_summary = self._heuristic_summarize(
            repo_name, files, readme_content, tech_stack
        )

        return RepoSummary(
            repo_name=repo_name,
            description=heuristic_summary["description"],
            purpose=heuristic_summary["purpose"],
            tech_stack=tech_stack,
            dependencies=dependencies,
            project_size=project_size,
            key_features=heuristic_summary["key_features"],
            file_tree=file_tree,
            confidence_score=heuristic_summary["confidence"],
            summary_method="heuristic",
            app_type=heuristic_summary.get("app_type"),
        )

    def _build_code_context(
        self, files: List[Dict], readme_content: Optional[str]
    ) -> str:
        """Build rich context from code files for AI analysis."""
        from utils import sort_files_by_priority, truncate_file_content

        context_parts = []
        char_limit = 28000
        current_chars = 0

        # Include README
        if readme_content:
            readme_truncated = truncate_file_content(readme_content, 100)
            context_parts.append(f"=== README.md ===\n{readme_truncated}")
            current_chars += len(readme_truncated)

        # Categorize files by importance
        page_files = []
        component_files = []
        model_files = []
        other_files = []

        for file in files:
            path = file.get("path", "").lower()
            content = file.get("content", "")

            # Skip tiny files and configs
            if len(content) < 100:
                continue
            if any(x in path for x in [".config", ".lock", "node_modules", ".git"]):
                continue

            # Categorize
            if any(
                x in path
                for x in ["page.", "page/", "pages/", "screen", "views/", "app/"]
            ):
                page_files.append(file)
            elif any(x in path for x in ["component", "widget"]):
                component_files.append(file)
            elif any(x in path for x in ["model", "schema", "type", "interface"]):
                model_files.append(file)
            else:
                other_files.append(file)

        # Priority: pages > models > components > other
        prioritized = (
            page_files[:10] + model_files[:5] + component_files[:5] + other_files[:5]
        )

        for file in prioritized:
            if current_chars >= char_limit:
                break

            path = file.get("path", "")
            content = file.get("content", "")

            # Extract meaningful code
            extracted = self._extract_meaningful_code(content, path)
            if extracted and len(extracted) > 50:
                entry = f"\n=== {path} ===\n{extracted}"
                context_parts.append(entry)
                current_chars += len(entry)

        return "\n".join(context_parts)

    def _extract_meaningful_code(self, content: str, path: str) -> str:
        """Extract meaningful parts of code - focus on business logic."""
        lines = content.split("\n")
        meaningful_lines = []
        max_lines = 80

        # Patterns indicating business logic
        important_patterns = [
            # Component/function definitions
            r"^(export|const|function|class|interface|type|def|func)\s+\w+",
            # JSX with meaningful content
            r"<[A-Z]\w+[^>]*>",
            # Business domain keywords (expanded)
            r"(booking|book|reserve|reservation|appointment|schedule|slot|available)",
            r"(venue|turf|ground|court|field|stadium|arena|pitch|sports)",
            r"(player|team|match|game|tournament|league)",
            r"(cart|checkout|order|payment|price|product|shop|store)",
            r"(user|profile|account|auth|login|register)",
            r"(dashboard|admin|manage|settings)",
            # UI text that reveals purpose
            r"(title|heading|label|button|placeholder)\s*[=:]\s*['\"]",
            r"['\"]Book\s|['\"]Reserve\s|['\"]Schedule\s",
            # Data fetching
            r"(fetch|get|post|create|update|delete)\w*\s*\(",
            # State management
            r"(useState|useEffect|useQuery|useMutation)",
        ]

        for i, line in enumerate(lines):
            if len(meaningful_lines) >= max_lines:
                break

            stripped = line.strip()
            if not stripped or stripped.startswith("//") or stripped.startswith("#"):
                continue

            # Check if line is important
            is_important = any(
                re.search(pattern, line, re.IGNORECASE)
                for pattern in important_patterns
            )

            # Include imports (limited), important lines, and exports
            if i < 20 or is_important:
                meaningful_lines.append(line)

        return "\n".join(meaningful_lines)

    def _groq_summarize(
        self, repo_name: str, code_context: str, tech_stack: Dict
    ) -> Optional[Dict]:
        """Generate summary using Groq's fast LLM."""
        if not self.groq_client:
            return None

        frameworks = tech_stack.get("frameworks", [])
        languages = tech_stack.get("languages", [])
        tech_str = (
            ", ".join(frameworks + languages)
            if (frameworks or languages)
            else "Unknown"
        )

        prompt = f"""You are analyzing a GitHub repository called "{repo_name}".

TECH STACK: {tech_str}

CODE FROM THE REPOSITORY:
{code_context}

YOUR TASK: Carefully read the code and determine what this application DOES for users.

ANALYSIS STEPS:
1. Look at page/screen component names - they reveal the app's sections
2. Find UI text (titles, buttons, labels) - they describe features
3. Identify data models/types - they show what the app manages
4. Check API calls/functions - they reveal user actions
5. Look for domain-specific keywords

IMPORTANT DISTINCTIONS:
- If you see "venue", "turf", "ground", "court", "booking", "slot", "timing" → It's a SPORTS VENUE/TURF BOOKING app
- If you see "cart", "product", "checkout", "shop" → It's an E-COMMERCE app  
- If you see "post", "feed", "follow", "like" → It's a SOCIAL MEDIA app
- If you see "course", "lesson", "student" → It's an EDUCATION app
- Don't confuse UI components like "Menu" (navigation) with food/restaurant features

Respond with ONLY this JSON (no markdown, no extra text):
{{"app_type": "Specific App Type (e.g., Sports Turf Booking Platform, E-commerce Store, etc.)", "description": "2-3 sentences explaining what users can do with this app. Be specific about the domain.", "purpose": "A [type] that allows users to [main actions]", "key_features": ["Specific feature 1", "Specific feature 2", "Specific feature 3", "Specific feature 4", "Specific feature 5"]}}"""

        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert code analyst. You identify what applications DO for end users by reading their source code. Focus on the BUSINESS DOMAIN, not technical implementation. Always respond with valid JSON only, no markdown formatting.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=700,
                temperature=0.1,
            )

            result_text = response.choices[0].message.content.strip()

            # Clean JSON
            if "```" in result_text:
                result_text = re.sub(r"```json?\s*", "", result_text)
                result_text = result_text.replace("```", "")
            result_text = result_text.strip()

            return json.loads(result_text)
        except json.JSONDecodeError as e:
            print(f"Groq JSON parse error: {e}")
            return None
        except Exception as e:
            print(f"Groq API error: {e}")
            return None

    def _openai_summarize(
        self, repo_name: str, code_context: str, tech_stack: Dict
    ) -> Optional[Dict]:
        """Generate summary using OpenAI."""
        if not self.openai_client:
            return None

        frameworks = tech_stack.get("frameworks", [])
        languages = tech_stack.get("languages", [])
        tech_str = (
            ", ".join(frameworks + languages)
            if (frameworks or languages)
            else "Unknown"
        )

        prompt = f"""Analyze repository "{repo_name}" (Tech: {tech_str}).

CODE:
{code_context}

Read the code carefully. Identify what this app DOES for users.
Look at: component names, UI text, data models, API calls.

IMPORTANT: 
- "venue/turf/court/booking/slot" = Sports Booking App
- "cart/product/checkout" = E-commerce
- Don't confuse UI "Menu" components with food apps

JSON response only:
{{"app_type": "Specific type", "description": "What users can do", "purpose": "One sentence", "key_features": ["f1", "f2", "f3", "f4", "f5"]}}"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Expert code analyst. Identify app purpose from code. JSON only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,
                temperature=0.1,
            )

            result_text = response.choices[0].message.content.strip()
            if "```" in result_text:
                result_text = re.sub(r"```json?\s*", "", result_text)
                result_text = result_text.replace("```", "")

            return json.loads(result_text)
        except Exception as e:
            print(f"OpenAI error: {e}")
            return None

    def _heuristic_summarize(
        self,
        repo_name: str,
        files: List[Dict],
        readme_content: Optional[str],
        tech_stack: Dict[str, List[str]],
    ) -> Dict:
        """Production-ready heuristic analysis with deep code scanning."""
        from utils import extract_project_description

        # Deep code analysis
        analysis = self._deep_code_analysis(files)

        # Get description from README/package.json
        desc_info = extract_project_description(files, readme_content)

        # Build results
        detected_app_type = analysis["app_type"]
        detected_keywords = analysis["keywords"]
        features = analysis["features"]
        confidence = 0.55

        # Build purpose
        frameworks = tech_stack.get("frameworks", [])
        languages = tech_stack.get("languages", [])

        if detected_app_type:
            purpose = f"A {detected_app_type}"
            if frameworks:
                purpose += f" built with {', '.join(frameworks[:2])}"
            confidence += 0.15
        elif frameworks:
            purpose = f"A {', '.join(frameworks[:2])} application"
        elif languages:
            purpose = f"A {', '.join(languages[:2])} project"
        else:
            purpose = "A software project"

        # Build description
        extracted_desc = desc_info.get("description", "")
        if (
            extracted_desc
            and len(extracted_desc) > 40
            and "localhost" not in extracted_desc.lower()
            and "edit the file" not in extracted_desc.lower()
        ):
            description = extracted_desc
            confidence += 0.1
        elif detected_app_type and detected_keywords:
            description = f"{repo_name} is {purpose.lower()}. Key features include {', '.join(detected_keywords[:4])} functionality."
        else:
            description = f"{repo_name} - {purpose}."

        # Adjust confidence
        if detected_app_type and len(detected_keywords) >= 4:
            confidence += 0.15
        if features:
            confidence += 0.05 * min(len(features), 3)

        return {
            "app_type": detected_app_type,
            "description": description,
            "purpose": purpose,
            "key_features": features[:6],
            "confidence": min(max(confidence, 0.45), 0.85),
        }

    def _deep_code_analysis(self, files: List[Dict]) -> Dict:
        """
        Deep analysis of code content to detect app type.
        Uses weighted keyword matching with context awareness.
        """
        # Domain patterns with WEIGHTED keywords
        # Higher weight = stronger indicator
        domains = {
            "Sports Turf/Venue Booking Platform": {
                "keywords": {
                    # Very strong indicators (weight 5)
                    "turf": 5,
                    "turfs": 5,
                    "booking turf": 5,
                    "ground booking": 5,
                    "court booking": 5,
                    "venue booking": 5,
                    # Strong indicators (weight 3)
                    "sports venue": 3,
                    "book venue": 3,
                    "book slot": 3,
                    "available slot": 3,
                    "time slot": 3,
                    "slot booking": 3,
                    "playground": 3,
                    "arena": 3,
                    "stadium": 3,
                    "ground": 2,
                    "court": 2,
                    "field": 2,
                    "pitch": 2,
                    # Medium indicators (weight 2)
                    "booking": 2,
                    "reservation": 2,
                    "schedule": 2,
                    "player": 2,
                    "match": 2,
                    "game": 2,
                    "sports": 2,
                    # Weak indicators (weight 1)
                    "venue": 1,
                    "location": 1,
                    "timing": 1,
                },
                "negative": ["food", "restaurant", "cuisine", "dish", "recipe"],
            },
            "E-commerce/Online Shopping Platform": {
                "keywords": {
                    "add to cart": 5,
                    "shopping cart": 5,
                    "checkout": 4,
                    "product listing": 4,
                    "buy now": 4,
                    "cart": 3,
                    "order": 2,
                    "product": 2,
                    "shop": 2,
                    "price": 2,
                    "inventory": 2,
                    "shipping": 2,
                    "discount": 2,
                    "coupon": 2,
                    "wishlist": 2,
                },
                "negative": ["booking", "turf", "venue", "court"],
            },
            "Food Delivery/Restaurant Platform": {
                "keywords": {
                    "food delivery": 5,
                    "order food": 5,
                    "restaurant menu": 4,
                    "food order": 4,
                    "cuisine": 3,
                    "dish": 3,
                    "restaurant": 3,
                    "delivery": 2,
                    "dine": 2,
                    "takeaway": 2,
                    "recipe": 2,
                },
                "negative": ["turf", "ground", "court", "venue booking"],
            },
            "Social Media Platform": {
                "keywords": {
                    "news feed": 5,
                    "timeline": 4,
                    "follow user": 4,
                    "social network": 4,
                    "post": 2,
                    "feed": 2,
                    "follow": 3,
                    "like": 2,
                    "comment": 2,
                    "share": 2,
                    "friend": 2,
                },
                "negative": [],
            },
            "Task/Project Management Tool": {
                "keywords": {
                    "kanban board": 5,
                    "project management": 4,
                    "task list": 4,
                    "sprint": 3,
                    "task": 2,
                    "project": 2,
                    "todo": 3,
                    "milestone": 2,
                    "assign": 2,
                    "deadline": 2,
                },
                "negative": [],
            },
            "Learning/Education Platform": {
                "keywords": {
                    "online course": 5,
                    "e-learning": 5,
                    "course content": 4,
                    "student dashboard": 4,
                    "course": 3,
                    "lesson": 3,
                    "student": 2,
                    "teacher": 2,
                    "quiz": 2,
                    "exam": 2,
                    "enroll": 3,
                    "classroom": 2,
                },
                "negative": [],
            },
            "Real Estate/Property Platform": {
                "keywords": {
                    "property listing": 5,
                    "real estate": 5,
                    "house for sale": 4,
                    "property": 3,
                    "listing": 2,
                    "house": 2,
                    "apartment": 2,
                    "rent": 2,
                    "buy property": 3,
                    "agent": 2,
                    "mortgage": 2,
                },
                "negative": [],
            },
            "Healthcare/Medical Platform": {
                "keywords": {
                    "patient record": 5,
                    "medical record": 5,
                    "doctor appointment": 4,
                    "patient": 3,
                    "doctor": 3,
                    "appointment": 2,
                    "medical": 2,
                    "clinic": 2,
                    "prescription": 3,
                    "health": 2,
                },
                "negative": [],
            },
        }

        # Collect all code content
        all_content = ""
        for file in files:
            path = file.get("path", "").lower()
            content = file.get("content", "")

            # Skip non-code files
            if not any(
                ext in path
                for ext in [
                    ".tsx",
                    ".jsx",
                    ".ts",
                    ".js",
                    ".vue",
                    ".py",
                    ".go",
                    ".java",
                    ".rb",
                ]
            ):
                continue
            if any(
                skip in path
                for skip in [
                    "test",
                    "spec",
                    ".config",
                    "node_modules",
                    ".min.",
                    "bundle",
                ]
            ):
                continue

            all_content += " " + content.lower()

        # Score each domain
        domain_scores: Dict[str, Tuple[int, List[str]]] = {}

        for domain, config in domains.items():
            score = 0
            found_keywords = []

            # Check for negative keywords first
            has_negative = any(neg in all_content for neg in config.get("negative", []))

            for keyword, weight in config["keywords"].items():
                count = all_content.count(keyword.lower())
                if count > 0:
                    # Apply diminishing returns for repeated keywords
                    contribution = weight * min(count, 5)
                    if has_negative:
                        contribution = (
                            contribution // 2
                        )  # Reduce if negative keywords present
                    score += contribution
                    found_keywords.append(keyword)

            if score > 0:
                domain_scores[domain] = (score, found_keywords)

        # Find best match
        if not domain_scores:
            return {"app_type": None, "keywords": [], "features": []}

        best_domain = max(domain_scores.items(), key=lambda x: x[1][0])
        app_type = (
            best_domain[0] if best_domain[1][0] >= 8 else None
        )  # Minimum threshold

        # Extract features from code
        features = self._extract_features_from_code(all_content, files)

        return {
            "app_type": app_type,
            "keywords": best_domain[1][1][:6] if app_type else [],
            "features": features,
            "score": best_domain[1][0] if domain_scores else 0,
        }

    def _extract_features_from_code(
        self, all_content: str, files: List[Dict]
    ) -> List[str]:
        """Extract features based on code patterns."""
        features = []
        file_paths = [f.get("path", "").lower() for f in files]

        feature_checks = [
            (
                r"(login|signin|auth|authentication)",
                ["auth", "login"],
                "User Authentication",
            ),
            (
                r"(signup|register|registration)",
                ["signup", "register"],
                "User Registration",
            ),
            (
                r"(booking|reservation|reserve)",
                ["booking", "reservation"],
                "Booking System",
            ),
            (
                r"(payment|checkout|stripe|razorpay|paypal)",
                ["payment", "stripe", "razorpay"],
                "Payment Integration",
            ),
            (r"(upload|image upload|file upload)", ["upload"], "File Uploads"),
            (r"(search|filter|query)", ["search"], "Search & Filtering"),
            (r"(notification|push|alert)", ["notification"], "Notifications"),
            (
                r"(dashboard|analytics|chart|stats)",
                ["dashboard", "analytics"],
                "Dashboard/Analytics",
            ),
            (
                r"(map|location|geo|address|google maps)",
                ["map", "location"],
                "Location/Maps",
            ),
            (
                r"(review|rating|feedback|testimonial)",
                ["review", "rating"],
                "Reviews & Ratings",
            ),
            (r"(admin|manage|crud|backoffice)", ["admin"], "Admin Panel"),
            (r"(profile|account|settings)", ["profile", "settings"], "User Profiles"),
            (r"(chat|messaging|inbox|realtime)", ["chat", "message"], "Real-time Chat"),
            (r"(email|smtp|sendgrid|mailgun)", ["email"], "Email Integration"),
        ]

        for pattern, path_keywords, feature_name in feature_checks:
            # Check content
            if re.search(pattern, all_content, re.IGNORECASE):
                features.append(feature_name)
                continue
            # Check file paths
            if any(any(kw in path for kw in path_keywords) for path in file_paths):
                features.append(feature_name)

        return features[:8]


def create_summarizer(use_ai: bool = True) -> Summarizer:
    """Factory function to create a Summarizer."""
    return Summarizer(use_ai=use_ai)
