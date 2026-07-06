"""
run_session.py — orchestrates one Deliberate session.

Runs inside a single GitHub Actions job. Loops through rounds, calling each
active agent, committing the growing JSON log to the repo after every round,
and posting each round as a comment on the originating GitHub Issue. Ends on
a 10-minute soft timer (with a minimum of 3 rounds) or a hard cap of 5 rounds
— never on "reaching an answer."
"""

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

from agents import call_agent, CORE_AGENT_KEYS, QUESTION_AGENT_KEY

TIME_LIMIT_SECONDS = 10 * 60  # 10-minute soft cap
MIN_ROUNDS = 3
MAX_ROUNDS = 5
QUESTION_AGENT_ROUNDS = {3, 4}  # rounds where the "Question" agent joins

SESSIONS_DIR = Path("sessions")


def git_commit_and_push(session_id: str, message: str):
    subprocess.run(["git", "config", "user.name", "deliberate-bot"], check=True)
    subprocess.run(
        ["git", "config", "user.email", "deliberate-bot@users.noreply.github.com"],
        check=True,
    )
    subprocess.run(["git", "add", str(SESSIONS_DIR / f"{session_id}.json")], check=True)
    # Nothing to commit is not an error (e.g. identical content) — ignore failure.
    subprocess.run(["git", "commit", "-m", message], check=False)
    subprocess.run(["git", "push"], check=True)


def post_issue_comment(session_id: str, body: str):
    # Requires the GitHub CLI (gh) to be authenticated in the workflow via
    # GH_TOKEN / GITHUB_TOKEN env var.
    subprocess.run(
        ["gh", "issue", "comment", session_id, "--body", body],
        check=True,
    )


def format_round_comment(round_num: int, round_result: dict) -> str:
    lines = [f"**Round {round_num}**\n"]
    for agent_key, response in round_result.items():
        display_name = agent_key.capitalize()
        lines.append(f"**{display_name}:** {response}\n")
    return "\n".join(lines)


def run_session(question: str, session_id: str):
    SESSIONS_DIR.mkdir(exist_ok=True)
    session_path = SESSIONS_DIR / f"{session_id}.json"

    session = {
        "question": question,
        "session_id": session_id,
        "status": "in_progress",
        "rounds": [],
    }
    session_path.write_text(json.dumps(session, indent=2))

    start_time = time.time()
    round_num = 0

    while True:
        round_num += 1
        elapsed = time.time() - start_time

        # Stop conditions: hard cap always applies; soft timer only applies
        # once the minimum round count has been met.
        if round_num > MAX_ROUNDS:
            break
        if elapsed > TIME_LIMIT_SECONDS and round_num > MIN_ROUNDS:
            break

        active_agents = list(CORE_AGENT_KEYS)
        if round_num in QUESTION_AGENT_ROUNDS:
            active_agents.append(QUESTION_AGENT_KEY)

        round_result = {}
        for agent_key in active_agents:
            response = call_agent(agent_key, question, session["rounds"])
            round_result[agent_key] = response

        session["rounds"].append(round_result)
        session_path.write_text(json.dumps(session, indent=2))

        git_commit_and_push(session_id, f"Deliberate: round {round_num}")
        post_issue_comment(session_id, format_round_comment(round_num, round_result))

    session["status"] = "timed_out"
    session_path.write_text(json.dumps(session, indent=2))
    git_commit_and_push(session_id, "Deliberate: session ended (timed_out)")
    post_issue_comment(
        session_id,
        "**Session ended.** No final answer by design — this was a live "
        "deliberation, not a resolution. The full record is above.",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", required=True)
    parser.add_argument("--session_id", required=True)
    args = parser.parse_args()

    run_session(args.question, args.session_id)
