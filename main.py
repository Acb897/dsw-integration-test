import os
import requests
import logging
from fastapi import FastAPI, Request
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load .env file
load_dotenv()

app = FastAPI()

# Read environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
CHAPTER_REPOS = {
    "Self-Assessment to Join the Virtual Platform Curated Network": os.getenv("REPO_SELF_ASSESSMENT"),
    "Motivation and Scope": os.getenv("REPO_MOTIVATION"),
    "Data analysis facilities": os.getenv("REPO_DATA_ANALYSIS"),
    "Reference datasets": os.getenv("REPO_REFERENCE_DATASETS"),
    "Objectives of co-creation": os.getenv("REPO_OBJECTIVES"),
    "General information on data": os.getenv("REPO_GENERAL_INFO"),
    "Current status of the data": os.getenv("REPO_CURRENT_STATUS")
}

# Validate environment variables
if not GITHUB_TOKEN or any(repo is None for repo in CHAPTER_REPOS.values() if repo is not None):
    missing_vars = [key for key, value in CHAPTER_REPOS.items() if value is None]
    raise RuntimeError(f"Set GITHUB_TOKEN and missing REPO_* environment variables: {missing_vars}")

@app.get("/")
async def root():
    return {"message": "DSW → GitHub webhook listener is running"}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse request JSON: {str(e)}")
        return {"status": "Failed", "error": "Invalid JSON payload"}

    # Extract questionnaire UUID and name for the issue title
    questionnaire = data.get("questionnaire", {})
    questionnaire_uuid = questionnaire.get("uuid", "unknown")
    questionnaire_name = questionnaire.get("name", "Unknown Questionnaire")
    title = f"[Automated] DSW Response: {questionnaire_name} ({questionnaire_uuid})"

    # Build GitHub issue body
    body = f"# Questionnaire Answers: {questionnaire_name}\n\n"
    body += "Below are the responses submitted for the questionnaire.\n\n"
    body += "## Table of Contents\n"
    for chapter in data.get("report", {}).get("chapters", []):
        chapter_title = chapter.get("title", "Unknown Chapter")
        # Convert chapter title to a valid anchor link (lowercase, replace spaces with hyphens)
        anchor = chapter_title.lower().replace(" ", "-").replace(".", "").replace(":", "")
        body += f"- [{chapter_title}](#{anchor})\n"
    body += "\n---\n"

    # Build mapping of question_uuid to chapter title and question title
    question_to_chapter = {}
    question_to_title = {}
    chapters = data.get("report", {}).get("chapters", [])
    for chapter in chapters:
        chapter_title = chapter.get("title", "Unknown Chapter")
        logger.info(f"Chapter title in data: {chapter_title}")
        for q_uuid in chapter.get("questionUuids", []):
            question_to_chapter[q_uuid] = chapter_title
            question = data.get("knowledgeModel", {}).get("entities", {}).get("questions", {}).get(q_uuid, {})
            question_to_title[q_uuid] = question.get("title", "Unknown Question")

    # Build mapping of answer_uuid to label for OptionQuestions
    answer_to_label = {}
    answers = data.get("knowledgeModel", {}).get("entities", {}).get("answers", {})
    for answer_uuid, answer in answers.items():
        answer_to_label[answer_uuid] = answer.get("label", "No Label")

    # Build mapping of choice_uuid to label for MultiChoiceQuestions
    choice_to_label = {}
    choices = data.get("knowledgeModel", {}).get("entities", {}).get("choices", {})
    for choice_uuid, choice in choices.items():
        choice_to_label[choice_uuid] = choice.get("label", "No Label")

    # Process all questions from chapters and track answered chapters
    question_replies = {}
    chapters_with_answers = set()
    replies = questionnaire.get("replies", {})
    for reply_path, reply in replies.items():
        parts = reply_path.split(".")
        question_uuid = parts[-1] if len(parts) <= 2 else parts[1]
        reply_value = reply.get("value", {})
        reply_type = reply_value.get("type", "")
        answer_text = ""

        if reply_type == "AnswerReply":
            answer_uuid = reply_value.get("value", "")
            answer_text = answer_to_label.get(answer_uuid, "No Answer")
        elif reply_type == "MultiChoiceReply":
            choice_uuids = reply_value.get("value", [])
            choices = [choice_to_label.get(uuid, "Unknown Choice") for uuid in choice_uuids]
            answer_text = "\n- " + "\n- ".join(choices) if choices else "No Choices Selected"
        elif reply_type == "StringReply":
            answer_text = reply_value.get("value", "No Value Provided")
        else:
            answer_text = "Unknown Reply Type"

        question_replies[question_uuid] = answer_text
        chapter_title = question_to_chapter.get(question_uuid, None)
        if chapter_title and answer_text != "Unanswered" and answer_text != "No Choices Selected":
            chapters_with_answers.add(chapter_title)
            logger.info(f"Reply for question {question_uuid} in {chapter_title}: type={reply_type}, text={answer_text}")

    logger.info(f"Chapters with answers: {chapters_with_answers}")

    # Build the issue body with all chapters
    for chapter in chapters:
        chapter_title = chapter.get("title", "Unknown Chapter")
        body += f"\n## {chapter_title}\n\n"
        body += "| **Question** | **Answer** |\n"
        body += "|-------------|-----------|\n"
        for q_uuid in chapter.get("questionUuids", []):
            question_title = question_to_title.get(q_uuid, "Unknown Question")
            answer_text = question_replies.get(q_uuid, "Unanswered")
            # Escape pipes in question and answer text to prevent breaking the table
            question_title = question_title.replace("|", "\\|")
            answer_text = answer_text.replace("|", "\\|").replace("\n", "<br>")
            body += f"| {question_title} | {answer_text} |\n"
        body += "\n---\n"

    # Submit the issue to repositories corresponding to chapters with answers
    results = []
    unique_repos = set()
    for chapter_title in chapters_with_answers:
        repo = CHAPTER_REPOS.get(chapter_title)
        if not repo:
            results.append({"chapter": chapter_title, "status": "Failed", "error": "No repository mapped for this chapter"})
            logger.error(f"No repository for chapter: {chapter_title}")
            continue
        if repo in unique_repos:
            results.append({"chapter": chapter_title, "status": "Skipped", "reason": f"Already submitted to {repo}"})
            logger.info(f"Skipping duplicate submission to {repo} for chapter: {chapter_title}")
            continue
        unique_repos.add(repo)

        logger.info(f"Submitting issue to repository: {repo} for chapter: {chapter_title}")

        # Call GitHub API to create the issue
        url = f"https://api.github.com/repos/{repo}/issues"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        payload = {"title": title, "body": body}
        try:
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 201:
                results.append({"chapter": chapter_title, "status": "Issue created", "url": response.json()["html_url"]})
                logger.info(f"Success: Issue created in {repo} for chapter: {chapter_title}")
            else:
                results.append({"chapter": chapter_title, "status": "Failed", "response": response.json()})
                logger.error(f"Failed: Issue creation in {repo} for chapter: {chapter_title}, response: {response.json()}")
        except Exception as e:
            results.append({"chapter": chapter_title, "status": "Failed", "error": str(e)})
            logger.error(f"Exception during issue creation in {repo} for chapter: {chapter_title}: {str(e)}")

    if not results:
        logger.info("No issues created: No chapters with answers found")
        return {"status": "No issues created", "reason": "No chapters with answers found"}

    return {"status": "Processed", "results": results}