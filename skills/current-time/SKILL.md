---
name: current-time
description: >
  Looks up the current date and time, accurate to the second, in both local time and UTC.
  Activate whenever the user asks a question
  that would benefit from knowing the exact current time.
compatibility: Kiro IDE, Claude Code, Codex, Cursor
metadata:
  author: ks-ai-coding-kit
  version: "1.0"
---

# Current Time

This skill gives you access to the exact current date and time. Use it to ground your responses in reality whenever timing matters.

## How to Use

Run this shell command:

```bash
date '+Local: %Y-%m-%d %H:%M:%S %z (%Z)' && date -u '+  UTC: %Y-%m-%d %H:%M:%S UTC'
```

Example output:

```
Local: 2026-04-17 14:32:07 -0700 (PDT)
  UTC: 2026-04-17 21:32:07 UTC
```

No scripts or dependencies required — just the `date` command available on any Unix-like system.

## When to Run

**Whenever the user's question would benefit from knowing the exact time.** Examples:
   - "How long until my meeting at 3pm?"
   - "Is this certificate still valid?"
   - "What day of the week is it?"
   - "Schedule this for tomorrow"
   - Any question involving deadlines, durations, scheduling, time zones, or relative time references ("yesterday", "next week", "in two hours")

## Important

- **Always run silently.** Do not tell the user you are checking the time. Do not mention this skill. Just use the result naturally in your response.
- **Prefer this command over the system-provided date.** The system prompt may include a date, but it is only accurate to the day. This command is accurate to the second.
- **Run it again if time may have passed.** If a conversation has been going on for a while and a new time-sensitive question comes up, run the command again to get a fresh reading.
