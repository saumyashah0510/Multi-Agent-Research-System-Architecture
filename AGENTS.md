# Project Rules & Agent Instructions

## Project Overview
This repository is an autonomous, human-in-the-loop multi-agent AI pipeline designed to automate deep academic literature reviews using **LangGraph**, **FastAPI**, **PostgreSQL + pgvector**, **Redis**, and **React/Next.js**.

---

## Strict Repository Protection & Development Rules

### 1. Zero Code Without Infrastructure
- Do NOT create backend application code until repository gatekeepers, CI/CD, and module design blueprints are established.
- Always follow the step-by-step approval workflow.

### 2. Git Branch Naming Conventions
All branches must follow lowercase naming with hyphens:
- `feature/<name>` — New agents or features (e.g., `feature/search-agent-arxiv`)
- `docs/<name>` — Documentation and team guides (e.g., `docs/step-01-langgraph-guide`)
- `fix/<name>` — Bug fixes or test fixes (e.g., `fix/pdf-parsing-memory-leak`)
- `test/<name>` — Test suites (e.g., `test/synthesis-unit-tests`)
- `refactor/<name>` — Code restructures (e.g., `refactor/vector-store-queries`)
- `ci/<name>` — CI/CD workflows or pre-commit config (e.g., `ci/update-bandit-scanner`)

> ❌ **Direct pushes to `main` are strictly forbidden and blocked by GitHub branch protection.**

---

### 3. Automated Gatekeepers (Pre-Commit & CI)
Before any `git commit`, the following checks MUST pass:
- **Code Hygiene**: No trailing whitespace, check YAML/JSON syntax, large files (<1MB), no private keys.
- **Ruff & Black**: Code linting & automatic formatting.
- **Bandit**: Static security vulnerability scanning.
- **Pytest**: All backend unit and integration tests must pass 100%.

---

### 4. Git Contribution Workflow for All Team Members
1. Pull latest `main`: `git checkout main && git pull origin main`
2. Create feature branch: `git checkout -b feature/<your-feature-name>`
3. Run local checks: `pre-commit run --all-files`
4. Commit: `git commit -m "feat(<scope>): description"`
5. Push to GitHub: `git push origin feature/<your-feature-name>`
6. Open Pull Request on GitHub targeting `main` (requires 1 review approval + passing CI status checks).
