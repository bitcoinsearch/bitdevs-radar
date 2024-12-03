import yaml
import git
import os
import re
from pathlib import Path
from datetime import datetime
import markdown
from bs4 import BeautifulSoup
import shutil
from typing import Dict, List, Tuple, Optional, Set
import tempfile
from loguru import logger


class Resource:
    def __init__(self, url: str):
        self.url = url
        self.titles = set()  # Track all titles used for this URL
        self.occurrences = (
            []
        )  # List of (date, source_file_url, category_path, title) tuples

    def add_occurrence(
        self, date: datetime, source_file_url: str, category_path: str, title: str
    ):
        self.titles.add(title)
        self.occurrences.append((date, source_file_url, category_path, title))
        logger.debug(f"Added occurrence for {self.url} from {source_file_url}")

    def to_dict(self):
        return {
            "url": self.url,
            "titles": list(self.titles),
            "count": len(self.occurrences),
            "occurrences": [
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "source": source_url,
                    "category": category_path,
                    "title_used": title,
                }
                for date, source_url, category_path, title in self.occurrences
            ],
        }


class HeadingTracker:
    def __init__(self):
        self.current_path = []

    def update_heading(self, text: str, level: int):
        """Update the current heading path based on new heading."""
        # Remove any headings at the same or lower level
        while self.current_path and self.get_last_level() >= level:
            self.current_path.pop()

        # Add the new heading
        self.current_path.append((level, text.strip()))
        logger.trace(f"Updated heading path: {self.get_category_path()}")

    def get_last_level(self) -> int:
        """Get the level of the last heading in the path."""
        return self.current_path[-1][0] if self.current_path else 0

    def get_category_path(self) -> str:
        """Get the full category path as a string."""
        return " / ".join(text for _, text in self.current_path)


class BitDevsRadar:
    def __init__(
        self,
        config_path: str,
        exclude_domains_path: str,
        start_date: Optional[datetime] = None,
    ):
        self.config_path = config_path
        self.exclude_domains_path = exclude_domains_path
        self.start_date = start_date
        self.temp_dir = tempfile.mkdtemp()
        self.resources = {}  # url -> Resource object
        logger.info(f"Initializing BitDevsRadar with temp directory: {self.temp_dir}")
        self.excluded_domains = self.load_excluded_domains()

    @property
    def scanned_resources(self) -> Dict:
        """Return the scanned resources in dictionary format."""
        return {
            "metadata": {
                "total_unique_urls": len(self.resources),
                "start_date": self.start_date.strftime("%Y-%m-%d")
                if self.start_date
                else None,
                "excluded_domains": list(self.excluded_domains),
            },
            "resources": {
                url: resource.to_dict()
                for url, resource in sorted(self.resources.items())
            },
        }

    def load_excluded_domains(self) -> Set[str]:
        """Load excluded domains from YAML file."""
        try:
            with open(self.exclude_domains_path, "r") as file:
                data = yaml.safe_load(file)
                domains = set(data.get("excluded_domains", []))
                logger.info(f"Loaded {len(domains)} excluded domains")
                return domains
        except FileNotFoundError:
            logger.warning(
                f"Exclusion file {self.exclude_domains_path} not found. Using empty exclusion list."
            )
            return set()
        except yaml.YAMLError as e:
            logger.error(f"Error parsing exclusion file: {e}")
            return set()

    def load_config(self) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, "r") as file:
                config = yaml.safe_load(file)
                logger.info(
                    f"Loaded configuration with {len(config['repositories'])} repositories"
                )
                return config
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise

    def clone_repo(self, repo_url: str, local_path: str) -> None:
        """Clone a repository to a local directory."""
        try:
            logger.debug(f"Cloning repository: {repo_url}")
            git.Repo.clone_from(repo_url, local_path)
            logger.success(f"Successfully cloned {repo_url}")
        except git.GitCommandError as e:
            logger.error(f"Error cloning {repo_url}: {e}")
            raise

    def parse_post_date(self, filename: str) -> datetime:
        """Extract date from Jekyll-style filename (YYYY-MM-DD-title.md)."""
        date_match = re.match(r"(\d{4}-\d{2}-\d{2})", filename)
        if date_match:
            return datetime.strptime(date_match.group(1), "%Y-%m-%d")
        logger.warning(f"Could not parse date from filename: {filename}")
        return None

    def extract_links_with_categories(
        self, markdown_content: str
    ) -> List[Tuple[str, str, str]]:
        """Extract all links and their text from markdown content, along with their categories."""
        html = markdown.markdown(markdown_content)
        soup = BeautifulSoup(html, "html.parser")

        links = []
        heading_tracker = HeadingTracker()

        for element in soup.descendants:
            if (
                element.name
                and not element.name.startswith("hr")
                and element.name.startswith("h")
            ):
                level = int(element.name[1])
                heading_tracker.update_heading(element.get_text(), level)

            elif element.name == "a":
                link = element.get("href", "").strip()
                text = element.get_text().strip()

                if not link or not text:
                    continue

                if any(excluded in link for excluded in self.excluded_domains):
                    logger.debug(f"Skipping excluded domain: {link}")
                    continue

                category_path = heading_tracker.get_category_path()
                links.append((text, link, category_path))

        logger.debug(f"Extracted {len(links)} links from content")
        return links

    def get_github_file_url(self, repo_url: str, relative_path: str) -> str:
        """Convert local file path to GitHub URL."""
        repo_url = repo_url.rstrip(".git")
        return f"{repo_url}/blob/master/{relative_path}"

    def process_repository(self, repo_info: Dict) -> None:
        """Process a single repository and update resource tracking."""
        repo_url = repo_info["url"]
        posts_dir = repo_info.get("posts_directory", "_posts")

        logger.debug(f"Processing repository: {repo_url}")
        repo_path = os.path.join(self.temp_dir, repo_url.split("/")[-1])
        self.clone_repo(repo_url, repo_path)

        posts_path = Path(repo_path) / posts_dir

        if not posts_path.exists():
            logger.error(f"Posts directory not found: {posts_path}")
            return

        post_count = 0
        for post_file in posts_path.glob("*.md"):
            post_date = self.parse_post_date(post_file.name)
            if not post_date or (self.start_date and post_date < self.start_date):
                logger.debug(f"Skipping post {post_file.name} (date: {post_date})")
                continue

            logger.debug(f"Processing post: {post_file.name}")
            with open(post_file, "r", encoding="utf-8") as f:
                content = f.read()

            links = self.extract_links_with_categories(content)
            relative_path = os.path.join(posts_dir, post_file.name)
            file_url = self.get_github_file_url(repo_url, relative_path)

            for text, url, category_path in links:
                if url not in self.resources:
                    self.resources[url] = Resource(url)
                self.resources[url].add_occurrence(
                    post_date, file_url, category_path, text
                )
            post_count += 1

        logger.info(f"Processed {post_count} posts from {repo_url}")

    def scan_all_repos(self) -> None:
        """Scan all repositories defined in the config file."""
        config = self.load_config()
        logger.info("Starting repository scan")

        for repo_info in config["repositories"]:
            try:
                self.process_repository(repo_info)
            except Exception as e:
                logger.error(f"Error processing repository {repo_info['url']}: {e}")

        logger.success(f"Scan completed. Found {len(self.resources)} unique resources")

    def cleanup(self):
        """Remove temporary directory and its contents."""
        logger.info(f"Cleaning up temporary directory: {self.temp_dir}")
        shutil.rmtree(self.temp_dir)
        logger.debug("Cleanup completed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
