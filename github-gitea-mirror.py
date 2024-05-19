import os
import requests
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Configuration from environment variables
GITHUB_API_URL = "https://api.github.com/user/repos"
GITEA_API_URL = os.getenv("GITEA_API_URL", "http://<your-gitea-instance>/api/v1")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITEA_TOKEN = os.getenv("GITEA_TOKEN")
GITEA_USER_ID = int(os.getenv("GITEA_USER_ID"))  # Ensure this is an integer
GITEA_USERNAME = os.getenv("GITEA_USERNAME")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# Headers for GitHub and Gitea
github_headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

gitea_headers = {
    "Authorization": f"token {GITEA_TOKEN}",
    "Content-Type": "application/json"
}

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Step 1: Get all GitHub repositories
def get_github_repos():
    repos = []
    page = 1
    while True:
        response = requests.get(f"{GITHUB_API_URL}?page={page}&per_page=100", headers=github_headers)
        if response.status_code != 200:
            logging.error(f"Failed to fetch GitHub repositories: {response.text}")
            raise Exception(f"Failed to fetch GitHub repositories: {response.text}")
        page_repos = response.json()
        if not page_repos:
            break
        repos.extend(page_repos)
        page += 1
    return repos

# Step 2: Delete existing private repository on Gitea
def delete_gitea_repo(repo_name):
    if DRY_RUN:
        logging.info(f"Dry-Run: Would delete repository {repo_name} on Gitea")
        return True

    delete_url = f"{GITEA_API_URL}/repos/{GITEA_USERNAME}/{repo_name}"
    response = requests.delete(delete_url, headers=gitea_headers)
    if response.status_code == 204:
        logging.info(f"Successfully deleted repository {repo_name} on Gitea")
    elif response.status_code == 404:
        logging.info(f"Repository {repo_name} does not exist on Gitea")
    else:
        logging.error(f"Failed to delete repository {repo_name} on Gitea: {response.text}")
    return response.status_code == 204 or response.status_code == 404

# Step 3: Add repositories to Gitea in mirror mode
def add_repo_to_gitea(repo):
    repo_name = repo['name']
    clone_url = repo['clone_url']

    # If the repository is private, include the username and token in the URL
    if repo['private']:
        clone_url = clone_url.replace('https://', f'https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@')
        # Delete existing repository if it exists
        if not delete_gitea_repo(repo_name):
            logging.error(f"Failed to delete existing repository {repo_name} on Gitea. Skipping creation.")
            return

    data = {
        "clone_addr": clone_url,
        "uid": GITEA_USER_ID,
        "repo_name": repo_name,
        "mirror": True,
        "private": repo['private'],  # Maintain the privacy setting
        "auth_username": "",  # Not needed when including credentials in the URL
        "auth_password": ""   # Not needed when including credentials in the URL
    }

    if DRY_RUN:
        logging.info(f"Dry-Run: Would add repository {repo_name} to Gitea with URL {clone_url}")
        return

    response = requests.post(f"{GITEA_API_URL}/repos/migrate", headers=gitea_headers, data=json.dumps(data))
    if response.status_code != 201:
        logging.error(f"Failed to add repository {repo_name} to Gitea: {response.text}")
    else:
        logging.info(f"Successfully added repository {repo_name} to Gitea")

# Main execution
if __name__ == "__main__":
    try:
        github_repos = get_github_repos()
        logging.info(f"Found {len(github_repos)} repositories on GitHub")
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            for repo in github_repos:
                executor.submit(add_repo_to_gitea, repo)
        
        logging.info("Repository mirroring process completed.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
