---
name: jobhunt
description: Korean developer job search, end to end — finds postings (Wanted, Jumpit, LinkedIn, Saramin, JobKorea, company career sites), scores them against the user's experience, builds a tailored resume A4 PDF, writes cover-letter answers, researches the company, prepares and drills interviews, and logs results. Use for finding or evaluating postings, a company-specific resume or cover letter, interview prep or mock interviews, and application status.
argument-hint: "[menu | onboard | scan | report | prep | evaluate <url> | tailor | cover | interview [plan|practice|debrief] | track | outcome]"
---

# jobhunt (pointer)

This file only lets agents that look for skills inside the repository (`.agents/skills/`, `.grok/skills/`, `.cursor/skills/`) find the skill. The router and every mode live at the repository root.

1. Find the repository root: from this file's folder, walk upward to the nearest folder that holds both `AGENTS.md` and `modes/`.
2. Read `<root>/SKILL.md` and follow it, passing on the same mode argument or request. Resolve every path against `<root>`, never against the current working directory.
