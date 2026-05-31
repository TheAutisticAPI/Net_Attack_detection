---
name: "🐛 Bug Report"
about: Report a bug or anomaly to help improve NIDS.
title: "[BUG] "
labels: bug
assignees: ""
---

**Describe the Bug**
A clear and concise description of what the bug is.

**Subsystem Affected**
Mark which component is throwing the error or exhibiting unexpected behavior:
- [ ] ML Track (`ml/`)
- [ ] API Core (`api/`)
- [ ] Analyst Dashboard (`web/`)
- [ ] Integration Pipeline (Docker / Compose)

**To Reproduce**
Steps to reproduce the behavior:
1. Spin up the environment using `docker compose up`
2. Perform action '...'
3. Send request to endpoint '...'
4. See error

**Expected Behavior**
A clear and concise description of what you expected to happen.

**Screenshots / Logs / Console Output**
If applicable, add screenshots, container logs, or API response errors to help explain your problem.

**Environment Context (please complete the following information):**
- OS: [e.g. Windows, Ubuntu]
- Python Version: [e.g. 3.10.12]
- Node Version: [e.g. 18.16.0]
- Docker/Compose Version: [e.g. 24.0.5]

**Additional Context**
Add any other context about the problem here (e.g. dataset files in use, custom Suricata configurations, etc.)
