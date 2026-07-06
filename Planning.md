# Deliberate — Planning

## Concept
A multi-agent system that deliberates on a user's question without ever converging
on a final answer. Instead of optimizing toward a single "correct" response, 3-4
agents with distinct, stable viewpoints react to each other over several rounds,
then the session ends on a timer/round cap — unresolved by design. The point isn't
to solve the question, it's to hold the live tension between perspectives visible
for as long as the session runs.

This is a prototype of a "perpetually humble, non-optimizing" posture — the goal
is continuous re-evaluation and preserved disagreement, not consensus.

## Core principles
- No forced convergence. Agents are explicitly instructed not to resolve toward
  agreement even when they find common ground.
- Disagreement is the signal, not noise to average away.
- Session ends on a timer or round cap, never on "reaching an answer."
- Entire stack must run for free (public repo + GitHub Actions + Claude Haiku).

## Agents (3 core + 1 occasional)
1. **Ground** — constraints/systems view. Evaluates practicality, cost, friction,
   existing incentives. Skeptical of elegant ideas that ignore real-world limits.
2. **Horizon** — long-arc/possibility view. Evaluates where trends lead over years/
   decades, less constrained by present friction. Takes "premature-sounding" ideas
   seriously.
3. **Ledger** — power/incentives view. Evaluates who benefits, who bears cost, who
   is least able to adapt. Most likely to complicate a "good for everyone" framing.
4. **Question** (occasional, rounds 3 and 4 only) — meta/framing view. Doesn't take
   an object-level position; interrogates the question itself and whether the other
   three agents are even answering the same question.

All agents:
- See the other agents' latest round and react to specific points (not summaries).
- Never stop at "I agree" — if there's common ground, they immediately locate what's
  still unresolved underneath it.
- Never produce a final answer, verdict, or synthesis, even if asked to.
- Keep responses short (2-4 sentences) — this is a live exchange, not an essay.

## Session mechanics
- **Trigger:** user opens a GitHub Issue; the Issue title is the question. GitHub's
  built-in `issues: opened` event fires the workflow automatically — no custom form
  or API glue needed.
- **Session ID:** the GitHub Issue number (e.g. issue #47 → `sessions/47.json`).
- **Timer:** 10-minute soft cap, with a minimum of 3 rounds guaranteed and a hard
  cap of 5 rounds (so short questions don't drag, and meaty ones don't spiral into
  repetition).
- **Round sequencing:**
  - Round 1: each core agent gives an independent initial take (no reacting yet).
  - Round 2: each core agent reacts to the other two.
  - Round 3: reactions deepen; Question agent joins to check the framing.
  - Round 4 (if time/round budget allows): another full round, Question agent may
    rejoin.
  - Round 5 (hard cap, only if under time limit): final round, session then ends.
- **Persistence:** no database. Each round is appended to `sessions/{issue_number}.json`
  and committed + pushed to the repo. Git history doubles as the audit trail.
- **Live visibility:** each round is also posted as a comment on the originating
  Issue via the GitHub CLI (`gh issue comment`), so the user can just watch the
  Issue thread fill in — no webpage required.
- **Optional viewer:** a static page hosted on GitHub Pages polls the raw JSON file
  and renders the thread more cleanly. Purely optional — the Issue thread is the
  source of truth and works standalone.
- **End state:** session status is marked `timed_out`, never `resolved`.

## Stack (all free tier)
- **Compute:** GitHub Actions on a public repo — free, uncapped minutes for standard
  Linux runners.
- **Model:** Claude Haiku via the Anthropic API — the only real cost, fractions of a
  cent per session.
- **Storage:** a committed JSON file per session (`sessions/{id}.json`) — git is the
  database. No Supabase, no external DB.
- **Trigger:** GitHub Issues (`issues: opened` event) — no custom form, no separate
  API call.
- **Viewer:** GitHub Pages serving `web/index.html`, polling the raw JSON via
  `raw.githubusercontent.com` with a cache-busting query param.

## Repo structure
```
/deliberate
  ├── Planning.md
  ├── .github/workflows/deliberate.yml   # triggers on Issue opened
  ├── run_session.py                     # timer/round orchestration loop
  ├── agents.py                          # persona prompts + Haiku call wrapper
  ├── sessions/
  │     └── {issue_number}.json          # live log, committed each round
  └── web/
        └── index.html                   # optional polling viewer, served via Pages
```

## Setup steps (one-time)
1. Create the repo as **public** (keeps Actions minutes free and unlimited).
2. Add `ANTHROPIC_API_KEY` as a repo secret (Settings → Secrets and variables →
   Actions).
3. Enable GitHub Pages: Settings → Pages → source = `main` branch, `/web` folder.
4. Confirm Issues are enabled on the repo (on by default).
5. Grant the Actions workflow permission to push commits and post Issue comments:
   Settings → Actions → General → Workflow permissions → "Read and write
   permissions."

## User flow
1. User opens a GitHub Issue with their question as the title.
2. Workflow fires automatically, runs the full session in one job (up to ~15 min
   wall clock, respecting the 10-min soft timer + round caps).
3. Each round is posted as a comment on the Issue as it completes, and committed to
   `sessions/{id}.json`.
4. User can watch the Issue thread directly, or open the GitHub Pages URL for a
   cleaner live view of the same session.
5. Session ends on timer/round cap — no final answer, status = `timed_out`.

## Known limitations / things to revisit
- `raw.githubusercontent.com` is CDN-cached; the optional viewer needs a cache-bust
  query param and may lag a few seconds to a minute behind the latest commit.
- A single long-running Actions job holds the whole 10-min session — simplest
  approach, but means the job is "busy" the whole time rather than resuming across
  multiple short-lived triggers.
- No concurrency handling — one session at a time per issue is fine; if two Issues
  fire at once, each runs as its own independent job (no shared state), which should
  be safe as-is.
- Agent prompts explicitly forbid convergence, but this needs real-world testing —
  models may still drift toward agreement over multiple rounds despite instruction.
