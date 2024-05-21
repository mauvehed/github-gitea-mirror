# GitHub to Gitea Repository Mirroring Script

This script mirrors repositories from GitHub to Gitea. It allows you to automatically copy repositories from your GitHub account to your Gitea instance, ensuring that the Gitea repositories are mirrors of the GitHub ones.

## Features

- Validate GitHub and Gitea credentials.
- Fetch all repositories from GitHub.
- Check existing repositories on Gitea and determine if they should be deleted or skipped.
- Add repositories to Gitea in mirror mode.
- Option to delete all existing repositories on Gitea before mirroring.

## Installation

### Prerequisites

- Python 3.8 or higher
- [Poetry](https://python-poetry.org/docs/#installation) for dependency management

### Setup

1. **Clone the repository**:

   ```sh
   git clone https://github.com/yourusername/yourrepository.git
   cd yourrepository

2. **Install dependencies**:

   ```sh
   poetry install
   ```

3. **Create a .env file in the project root directory with the following variables**:

   ```sh
   GITHUB_TOKEN=your_github_token
   GITEA_TOKEN=your_gitea_token
   GITEA_API_URL=https://your-gitea-instance/api/v1
   GITEA_USER_ID=your_gitea_user_id
   GITEA_USERNAME=your_gitea_username
   GITHUB_USERNAME=your_github_username
   DRY_RUN=false
   ```

## Usage

1. **Activate the virtual environment**:

   ```sh
   poetry shell
   ```

2. Run the script:

   ```sh
   python github-gitea-mirror.py
   ```

3. Follow the prompt to delete all existing repositories on Gitea:

   ```sh
   Do you want to delete all existing repositories on Gitea? (yes/no): 
   ```

## Development

### Development Dependencies

The development dependencies include mypy and types-requests for type checking.

### Adding Development Dependencies

To add development dependencies, use:

   ```sh
   poetry add --dev package_name
   ```

### Type Checking

To run type checking using mypy, use:

   ```sh
   mypy github-gitea-mirror.py
   ```

## Contributing

1. Fork the repository.
2. Create a new branch (git checkout -b feature-branch).
3. Commit your changes (git commit -am 'Add new feature').
4. Push to the branch (git push origin feature-branch).
5. Create a new Pull Request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [Gitea](https://github.com/go-gitea/gitea) for self-hosted Git service.

- [GitHub](https://www.github.com/) for community based Git service.
