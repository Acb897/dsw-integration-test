# DSW → GitHub Webhook Automation

This project listens for responses from a **Data Stewardship Wizard (DSW) questionnaire** and automatically creates GitHub issues with the submitted answers.

---

## Features

- Receives questionnaire responses via a webhook
- Processes answers and formats them into GitHub issues
- Fully containerized using **Docker** and **Docker Compose**
- Runs continuously with automatic restart

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed
- [Docker Compose](https://docs.docker.com/compose/install/) installed
- GitHub Personal Access Token (with `repo` permission)
- Repositories where issues will be created
- `.env` file with the following variables:

```env
GITHUB_TOKEN=your_github_token_here
REPO_SELF_ASSESSMENT=your_username/your_repo_here
REPO_GENERAL_INFO=your_username/your_repo_here
REPO_CURRENT_STATUS=your_username/your_repo_here
REPO_OBJECTIVES=your_username/your_repo_here
REPO_DATA_ANALYSIS=your_username/your_repo_here
REPO_REFERENCE_DATASETS=your_username/your_repo_here
