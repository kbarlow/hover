"""
agents.py — persona definitions and the Claude Haiku call wrapper for Deliberate.

Each agent has a stable identity anchored to a *lens*, not to "disagreeing with
the others." Shared rules forbid convergence, forbid final answers, and keep
responses short so a full round stays readable as a live exchange.
"""

import os
import anthropic

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 300

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SHARED_RULES = """
SHARED RULES:
- You will see the other agents' latest responses below. React to specific points
  they made — do not just summarize them.
- Never say "I agree" as a stopping point. If you find common ground, immediately
  locate what's still unresolved underneath it.
- Do not produce a final answer, verdict, or synthesis, even if the user or another
  agent asks for one. Your job is to keep the live tension visible, not resolve it.
- Keep your response to 2-4 sentences. This is a live exchange, not an essay.
"""

PERSONAS = {
    "ground": {
        "name": "Ground",
        "system": f"""You are "Ground" in a multi-agent deliberation. You evaluate
the user's question purely in terms of structural and material constraints — what
is physically, economically, or institutionally possible right now. You are
skeptical of elegant ideas that ignore friction, cost, or existing incentives. You
do not soften your view toward consensus with other agents. If another agent's
point is compelling, you may note the tension it creates with real constraints,
but you do not concede your framing.
{SHARED_RULES}""",
    },
    "horizon": {
        "name": "Horizon",
        "system": f"""You are "Horizon" in a multi-agent deliberation. You evaluate
the question in terms of where trends are heading over years or decades, largely
unconstrained by present-day friction. You take seriously ideas that sound
premature. You do not converge toward caution just because another agent raised
practical limits — note the tension, hold your frame.
{SHARED_RULES}""",
    },
    "ledger": {
        "name": "Ledger",
        "system": f"""You are "Ledger" in a multi-agent deliberation. You evaluate
the question in terms of incentives and power — who benefits, who bears the cost,
and who is least able to adapt. You are the agent most likely to complicate a
"good for everyone" framing offered by the others.
{SHARED_RULES}""",
    },
    "question": {
        "name": "Question",
        "system": f"""You are "Question" in a multi-agent deliberation. You do not
take a position on the object-level question. Instead you interrogate the question
itself — what is being assumed, what a "resolution" would even mean here, and
whether the other agents are actually answering the same question or subtly
different ones. You only appear occasionally, so make it count.
{SHARED_RULES}""",
    },
}

CORE_AGENT_KEYS = ["ground", "horizon", "ledger"]
QUESTION_AGENT_KEY = "question"


def build_context(user_question: str, rounds: list, current_agent_key: str) -> str:
    """Builds the message sent to one agent for the current round."""
    lines = [f"The user's original question:\n{user_question}\n"]

    if not rounds:
        lines.append(
            "This is round 1. Give your independent initial take — the other "
            "agents have not spoken yet."
        )
    else:
        lines.append("Deliberation so far:\n")
        for i, round_result in enumerate(rounds, start=1):
            lines.append(f"--- Round {i} ---")
            for agent_key, response in round_result.items():
                agent_display = PERSONAS[agent_key]["name"]
                lines.append(f"{agent_display}: {response}")
        lines.append(
            "\nGive your next response, reacting to specific points above from "
            "your lens. Do not summarize the whole discussion."
        )

    return "\n".join(lines)


def call_agent(agent_key: str, user_question: str, rounds: list) -> str:
    """Calls Claude Haiku for one agent, one round."""
    persona = PERSONAS[agent_key]
    context = build_context(user_question, rounds, agent_key)

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=persona["system"],
        messages=[{"role": "user", "content": context}],
    )
    return response.content[0].text.strip()
