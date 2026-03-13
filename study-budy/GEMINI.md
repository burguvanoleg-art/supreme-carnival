# Study-Buddy — Project Rules

This file contains foundational mandates and project-specific instructions for Gemini.

## Project Overview
Study-Buddy is an app where users paste text, and the AI explains it simply, generates quiz questions, and answers follow-up questions.

## Tech Stack
- **Language:** Python 3.12
- **Framework:** FastAPI (backend framework)
- **AI Brain:** Google Gemini API
- **External API:** Open-Meteo API (weather, free, no key)
- **Libraries:**
  - `requests` (HTTP calls)
  - `python-dotenv` (environment variables)
- **Structure:** Single file implementation in `main.py`.

## Coding Standards
- **Type Hints:** Required on all functions.
- **Documentation:** Docstring on every endpoint.
- **API Response Format:** Consistent JSON response: `{"status": "ok/error", "data": ...}`.
- **Secrets Management:** Environment variables for ALL secrets.
- **Error Handling:** `try/except` blocks on every endpoint.

## Gemini-Specific Rules
- **File Management:** Ask before creating new files.
- **Environment:** Do not modify `.env` files.
- **Robustness:** If an external API fails, return a graceful error.
- **Precedence:** These rules take absolute precedence over general defaults.
