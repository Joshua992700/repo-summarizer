import os
import requests
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class RepoData:
    repo_name: str
    files: list
    error: Optional[str] = None


class GoParserClient:
    """Client for communicating with the Go parser service."""

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize the API client.

        Args:
            base_url: Base URL of the Go parser service.
                     Defaults to GO_PARSER_URL env var or http://localhost:8080
        """
        self.base_url = base_url or os.getenv("GO_PARSER_URL", "http://localhost:8080")
        self.timeout = 120  # 2 minutes timeout for large repos

    def health_check(self) -> bool:
        """Check if the Go parser service is running."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def parse_repo(self, github_url: str) -> RepoData:
        """
        Parse a GitHub repository.

        Args:
            github_url: GitHub repository URL

        Returns:
            RepoData object containing parsed files

        Raises:
            ConnectionError: If the Go service is not reachable
            ValueError: If the response is invalid
        """
        try:
            response = requests.post(
                f"{self.base_url}/parse",
                json={"url": github_url},
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                data = response.json()
                return RepoData(
                    repo_name=data.get("repo_name", "unknown"),
                    files=data.get("files", []),
                    error=data.get("error"),
                )
            else:
                error_msg = response.json().get("error", "Unknown error")
                return RepoData(
                    repo_name="unknown",
                    files=[],
                    error=f"HTTP {response.status_code}: {error_msg}",
                )

        except requests.ConnectionError:
            raise ConnectionError(
                f"Cannot connect to Go parser service at {self.base_url}. "
                "Make sure the service is running: cd go-parser && go run main.go"
            )
        except requests.Timeout:
            raise TimeoutError(
                f"Request timed out after {self.timeout} seconds. "
                "The repository might be too large."
            )
        except requests.RequestException as e:
            raise ValueError(f"Request failed: {str(e)}")
        except (KeyError, ValueError) as e:
            raise ValueError(f"Invalid response from server: {str(e)}")


def create_client(base_url: Optional[str] = None) -> GoParserClient:
    """Factory function to create a GoParserClient."""
    return GoParserClient(base_url)
