import os
import logging
from logging.handlers import RotatingFileHandler
import sys
import requests
import json
from dotenv import load_dotenv
from typing import Optional, List, Dict

# Load environment variables from a .env file
load_dotenv()

# Configuration from environment variables
GITHUB_API_URL = "https://api.github.com/user/repos"
GITEA_API_URL = os.getenv("GITEA_API_URL", "http://<your-gitea-instance>/api/v1")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITEA_TOKEN = os.getenv("GITEA_TOKEN")
GITEA_USER_ID_STR: Optional[str] = os.getenv("GITEA_USER_ID")
GITEA_USERNAME = os.getenv("GITEA_USERNAME")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# Set up logging to write to a file
log_file = os.path.join(os.getcwd(), 'debug.log')
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
log_handler.setFormatter(log_formatter)
log_handler.setLevel(logging.DEBUG)

logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Default logging level set to INFO
logger.addHandler(log_handler)

# Uncomment the following line to enable debug logging
# logger.setLevel(logging.DEBUG)

# Check and validate environment variables
def validate_env_vars() -> int:
    """
    Validate and clean up environment variables.

    Ensures all required environment variables are set and converts GITEA_USER_ID
    to an integer after cleaning it up.

    Raises:
        ValueError: If any required environment variable is missing or if GITEA_USER_ID is not an integer.

    Returns:
        int: Cleaned and validated GITEA_USER_ID.
    """
    required_vars = {
        "GITEA_API_URL": GITEA_API_URL,
        "GITHUB_TOKEN": GITHUB_TOKEN,
        "GITEA_TOKEN": GITEA_TOKEN,
        "GITEA_USER_ID": GITEA_USER_ID_STR,
        "GITEA_USERNAME": GITEA_USERNAME,
        "GITHUB_USERNAME": GITHUB_USERNAME,
    }

    for var_name, var_value in required_vars.items():
        if not var_value:
            raise ValueError(f"Environment variable {var_name} is required.")
    
    logger.debug(f"GITEA_USER_ID_STR before cleanup: {GITEA_USER_ID_STR}")
    cleaned_user_id_str = GITEA_USER_ID_STR.split("#")[0].strip() if GITEA_USER_ID_STR else None
    logger.debug(f"GITEA_USER_ID_STR after cleanup: {cleaned_user_id_str}")

    if cleaned_user_id_str is None:
        raise ValueError("GITEA_USER_ID environment variable is required and must be an integer.")

    try:
        return int(cleaned_user_id_str)
    except ValueError as e:
        raise ValueError(
            "GITEA_USER_ID environment variable must be an integer."
        ) from e

GITEA_USER_ID = validate_env_vars()

# Headers for GitHub and Gitea
github_headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

gitea_headers = {
    "Authorization": f"token {GITEA_TOKEN}",
    "Content-Type": "application/json"
}

# Function to check GitHub credentials
def check_github_credentials() -> bool:
    """Check if the GitHub credentials are valid."""
    response = requests.get("https://api.github.com/user", headers=github_headers)
    if response.status_code == 200:
        logger.info("GitHub credentials are valid.")
        return True
    else:
        logger.error(f"GitHub credentials are invalid: {response.text}")
        return False

# Function to check Gitea credentials
def check_gitea_credentials() -> bool:
    """Check if the Gitea credentials are valid."""
    response = requests.get(f"{GITEA_API_URL}/user", headers=gitea_headers)
    if response.status_code == 200:
        logger.info("Gitea credentials are valid.")
        return True
    else:
        logger.error(f"Gitea credentials are invalid: {response.text}")
        return False

# Step 1: Get all GitHub repositories
def get_github_repos() -> List[Dict]:
    """Fetch all repositories from GitHub."""
    repos = []
    page = 1
    while True:
        response = requests.get(f"{GITHUB_API_URL}?page={page}&per_page=100", headers=github_headers)
        if response.status_code != 200:
            logger.error(f"Failed to fetch GitHub repositories: {response.text}")
            raise Exception(f"Failed to fetch GitHub repositories: {response.text}")
        page_repos = response.json()
        if not page_repos:
            break
        repos.extend(page_repos)
        page += 1
    return repos

# Step 2: Fetch all repositories from Gitea and check if the repository exists
def get_gitea_repos() -> List[Dict]:
    """Fetch all repositories from Gitea."""
    try:
        response = requests.get(f"{GITEA_API_URL}/user/repos", headers=gitea_headers)
        if response.status_code == 200:
            return response.json()
        logger.error(f"Failed to fetch repositories from Gitea: {response.text}")
        return []
    except Exception as e:
        logger.error(f"Failed to fetch repositories from Gitea: {e}")
        return []

def gitea_repo_exists(repo_name: str, gitea_repos: List[Dict]) -> Optional[Dict]:
    """Check if a repository exists on Gitea and return its details."""
    return next((repo for repo in gitea_repos if repo['name'] == repo_name), None)

# Step 3: Delete existing private repository on Gitea
def delete_gitea_repo(repo_name: str) -> bool:
    """Delete an existing repository on Gitea."""
    if DRY_RUN:
        logger.info(f"Dry-Run: Would delete repository {repo_name} on Gitea")
        return True

    delete_url = f"{GITEA_API_URL}/repos/{GITEA_USERNAME}/{repo_name}"
    response = requests.delete(delete_url, headers=gitea_headers)
    if response.status_code == 204:
        logger.info(f"Successfully deleted repository {repo_name} on Gitea")
        return True
    else:
        logger.error(f"Failed to delete repository {repo_name} on Gitea: {response.text}")
        return False

# Step 4: Add repositories to Gitea in mirror mode
def add_repo_to_gitea(repo: Dict) -> None:
    """Add a repository to Gitea in mirror mode."""
    repo_name = repo['name']
    clone_url = repo['clone_url']

    if repo['private']:
        clone_url = clone_url.replace('https://', f'https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@')

    data = {
        "clone_addr": clone_url,
        "uid": GITEA_USER_ID,
        "repo_name": repo_name,
        "mirror": True,
        "private": repo['private'],
        "auth_username": GITHUB_USERNAME if repo['private'] else "",
        "auth_password": GITHUB_TOKEN if repo['private'] else ""
    }

    if DRY_RUN:
        logger.info(f"Dry-Run: Would add repository {repo_name} to Gitea with URL {clone_url}")
        return

    try:
        response = requests.post(f"{GITEA_API_URL}/repos/migrate", headers=gitea_headers, data=json.dumps(data))
        if response.status_code == 201:
            logger.info(f"Successfully added repository {repo_name} to Gitea")
        elif response.json().get("message") == "The repository with the same name already exists.":
            logger.info(f"Repository {repo_name} already exists on Gitea. Skipping creation.")
        else:
            logger.error(f"Failed to add repository {repo_name} to Gitea: {response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"An exception occurred while adding repository {repo_name} to Gitea: {e}")

if __name__ == "__main__":
    try:
        # Validate credentials before proceeding
        if not check_github_credentials():
            logger.error("Invalid GitHub credentials. Exiting.")
            sys.exit(1)
        if not check_gitea_credentials():
            logger.error("Invalid Gitea credentials. Exiting.")
            sys.exit(1)

        delete_all_repos = input("Do you want to delete all existing repositories on Gitea? (yes/no): ").strip().lower()
        if delete_all_repos not in ['yes', 'no']:
            logger.error("Invalid input. Please enter 'yes' or 'no'. Aborting script.")
            sys.exit(1)

        # Step 1: Get GitHub repositories
        github_repos = get_github_repos()
        logger.info(f"Found {len(github_repos)} repositories on GitHub")

        # Cache Gitea repositories
        gitea_repos = get_gitea_repos()

        for repo in github_repos:
            repo_name = repo['name']

            if gitea_repo := gitea_repo_exists(repo_name, gitea_repos):
                if not gitea_repo.get('mirror'):
                    logger.info(f"Repository {repo_name} on Gitea is not a mirror. Skipping.")
                    continue
                if delete_all_repos == 'yes' and not delete_gitea_repo(repo_name):
                    continue

            # Step 4: Add repository to Gitea
            add_repo_to_gitea(repo)

        logger.info("Repository mirroring process completed.")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
