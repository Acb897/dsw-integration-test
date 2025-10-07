import os
import requests
from fastapi import FastAPI, Request
from dotenv import load_dotenv

# Load .env file
load_dotenv()

app = FastAPI()

# Read environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = os.getenv("REPO")

if not GITHUB_TOKEN or not REPO:
    raise RuntimeError("Set GITHUB_TOKEN and REPO environment variables in your .env file")

@app.get("/")
async def root():
    return {"message": "DSW → GitHub webhook listener is running"}

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()

    # Extract questionnaire UUID and name for the issue title
    questionnaire = data.get("questionnaire", {})
    questionnaire_uuid = questionnaire.get("uuid", "unknown")
    questionnaire_name = questionnaire.get("name", "Unknown Questionnaire")
    title = f"[Automated]DSW response from questionnaire {questionnaire_name} ({questionnaire_uuid})"

    # Build GitHub issue body
    body = "### Questionnaire Answers:\n\n"

    # Build mapping of question_uuid to chapter title and question title
    question_to_chapter = {}
    question_to_title = {}
    chapters = data.get("report", {}).get("chapters", [])
    for chapter in chapters:
        chapter_title = chapter.get("title", "Unknown Chapter")
        for q_uuid in chapter.get("questionUuids", []):
            question_to_chapter[q_uuid] = chapter_title
            # Find question title from knowledgeModel.entities.questions
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

    # Process all questions from chapters
    question_replies = {}
    replies = questionnaire.get("replies", {})
    for reply_path, reply in replies.items():
        # Extract question UUID from reply path (e.g., "chapter_uuid.question_uuid" or nested)
        parts = reply_path.split(".")
        # The question UUID is typically the second-to-last or last part, depending on nesting
        question_uuid = parts[-1] if len(parts) <= 2 else parts[1]
        reply_value = reply.get("value", {})
        reply_type = reply_value.get("type", "")
        answer_text = ""

        if reply_type == "AnswerReply":
            answer_uuid = reply_value.get("value", "")
            answer_text = answer_to_label.get(answer_uuid, "No Answer")
        elif reply_type == "MultiChoiceReply":
            choice_uuids = reply_value.get("value", [])
            answer_text = ", ".join([choice_to_label.get(uuid, "Unknown Choice") for uuid in choice_uuids]) or "No Choices Selected"
        elif reply_type == "StringReply":
            answer_text = reply_value.get("value", "No Value Provided")
        else:
            answer_text = "Unknown Reply Type"

        question_replies[question_uuid] = answer_text

    # Iterate through all chapters and questions to include answered and unanswered questions
    for chapter in chapters:
        chapter_title = chapter.get("title", "Unknown Chapter")
        body += f"**Chapter**: {chapter_title}\n\n"
        for q_uuid in chapter.get("questionUuids", []):
            question_title = question_to_title.get(q_uuid, "Unknown Question")
            answer_text = question_replies.get(q_uuid, "Unanswered")
            body += f"- **Question**: {question_title}\n"
            body += f"- **Answer**: {answer_text}\n\n"

    # Call GitHub API to create the issue
    url = f"https://api.github.com/repos/{REPO}/issues"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    payload = {"title": title, "body": body}

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 201:
        return {"status": "Issue created", "url": response.json()["html_url"]}
    else:
        return {"status": "Failed", "response": response.json()}