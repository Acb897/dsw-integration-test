# DSW → GitHub Webhook Automation

This project listens for responses from a **Data Stewardship Wizard (DSW) questionnaire** and automatically creates GitHub issues with the submitted answers.

---

## Features

- Receives questionnaire responses via a webhook
- Processes answers and formats them into GitHub issues
- Fully containerized using **Docker** and **Docker Compose**
- Optional public URL for testing with **ngrok** (local only)

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed
- [Docker Compose](https://docs.docker.com/compose/install/) installed
- GitHub Personal Access Token (with `repo` permission)
- Repository where issues will be created
- `.env` file with the following variables:

```env
GITHUB_TOKEN=your_github_token_here
REPO=your_username/your_repo_here
NGROK_AUTHTOKEN=your_ngrok_authtoken_here  # optional, only if using ngrok