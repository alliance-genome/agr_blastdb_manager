# BLAST DB Manager

## Overview
BLAST DB Manager is a tool designed to automate the creation and updating of BLAST (Basic Local Alignment Search Tool) databases. It utilizes GitHub Actions for workflow automation and runs on a self-hosted EC2 instance for enhanced control and customization.

## Features
- Automated BLAST database creation and updates
- Integration with GitHub Actions for CI/CD
- Custom runner setup on EC2 for specialized environment control
- Slack notifications for job status updates
- S3 synchronization for database storage and distribution

## Prerequisites
- An AWS account with EC2 and S3 access
- A GitHub repository
- Python 3.x installed on the EC2 instance
- Poetry for Python dependency management
- NCBI BLAST+ toolkit

## Setup

### 1. EC2 Instance Setup
1. Launch an EC2 instance with Amazon Linux 2023.
2. Install required software:
   ```bash
   sudo yum update -y
   sudo yum install -y python3 python3-pip ncbi-blast+
   pip3 install poetry
   ```

### 2. GitHub Actions Runner Setup
1. On your GitHub repository, go to Settings > Actions > Runners.
2. Click "New self-hosted runner" and follow the installation instructions for Linux.
3. Start the runner on your EC2 instance:
   ```bash
   cd actions-runner
   ./run.sh
   ```

### 3. Repository Setup
1. Clone your repository on the EC2 instance.
2. Create a `.github/workflows` directory in your repository.
3. Add the `update_blast_db.yml` workflow file to this directory.

### 4. Configuration
1. Create a `config/blast_config.yaml` file in your repository with the necessary configuration for your BLAST DB creation.
2. Set up the following secrets in your GitHub repository:
   - `GITHUB_WEBHOOK_SECRET`
   - `SLACK_TOKEN`
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`

## Usage

### Running the Workflow
The BLAST DB update workflow can be triggered in two ways:
1. Automatically on push to the `main` branch.
2. Manually from the Actions tab in your GitHub repository.

### Workflow Steps
1. Checkout the repository
2. Set up Python and Poetry
3. Install dependencies
4. Ensure BLAST is installed
5. Run the BLAST DB update script
6. Upload logs as artifacts

## Project Structure
```
your-repo/
├── .github/
│   └── workflows/
│       └── update_blast_db.yml
├── src/
│   └── create_blast_db.py
├── config/
│   └── blast_config.yaml
├── README.md
└── pyproject.toml
```

## Customization
- Modify `src/create_blast_db.py` to adjust the BLAST DB creation process.
- Update `config/blast_config.yaml` to change BLAST DB configurations.
- Edit `.github/workflows/update_blast_db.yml` to alter the CI/CD workflow.

## Troubleshooting
- Check the GitHub Actions logs for detailed error messages.
- Ensure the EC2 instance has the necessary permissions to access required AWS services.
- Verify that all required secrets are correctly set in the GitHub repository settings.

## Contributing
Contributions to improve BLAST DB Manager are welcome. Please follow these steps:
1. Fork the repository
2. Create a new branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License
[Specify your license here]

## Contact
[Your Name or Organization] - [Your Email]

Project Link: [https://github.com/your_username/repo_name](https://github.com/your_username/repo_name)
