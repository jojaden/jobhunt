---
name: jobhunt
description: Korean developer job search, end to end — finds postings (Wanted, Jumpit, LinkedIn, Saramin, JobKorea, company career sites), scores them against the user's experience, builds a tailored resume A4 PDF, writes cover-letter answers, researches the company, prepares and drills interviews, and logs results. Use for finding or evaluating postings, a company-specific resume or cover letter, interview prep or mock interviews, and application status.
argument-hint: "[menu | onboard | scan | report | prep | evaluate <url> | tailor | cover | interview [plan|practice|debrief] | track | outcome]"
---

# jobhunt (plugin pointer)

This plugin carries only this file. The router, every mode and the scripts come with the `jobhunt` command (installed with `uv tool install`), so the instructions always match the installed scripts.

1. Run `jobhunt where`. The folder on its `함께 배포된 파일` line is the skill folder.
2. Read `SKILL.md` in that folder and follow it, passing on the same mode argument or request. Resolve `modes/…` and `references/…` against that folder, never against this plugin.
3. If `jobhunt` is missing, ask the user to install it with the one-line installer, then continue from step 1:

   ```
   curl -fsSL https://raw.githubusercontent.com/jojaden/jobhunt/main/install.sh | bash
   ```
