# Homework 4 — Campus Customs Shop + Chatbot

This folder is the submission root for Homework 4.

## Project conventions

- Runtime/source code belongs at this level.
- Reusable model instructions belong in `prompts/`.
- Generated, grader-facing artifacts belong in `output/`.
- Supporting input files belong in `assets/` or `data/`.
- The human-readable AI interaction record is `AI_prompts.md`.
- Database schema notes are in `database_analysis.md`.
- Keep secrets in the workspace environment; never commit API keys or passwords.

## Public-repository setup

This repository intentionally excludes the private SQLite database and product
photography. They are needed only for local development. Copy `.env.example` to
`.env` and add your own Portkey key; never commit `.env`. Before running the
site locally, place the supplied database at `data/campus_customs.db` and the
product images at `frontend/public/data/products/`.

The supplied SQLite database is available locally at `data/campus_customs.db`. The original source database was supplied separately at `/Users/marydimitrov/Downloads/data 2/campus_customs.db`.

## Problem 3 — run the website

From the `backend/` folder, start the API with `uvicorn main:app --reload --port 8000`. In a second terminal, run `cd frontend && npm install && npm run dev`, then open `http://localhost:5173`.

The API listens on port 8000; the Vite development server proxies `/api` requests to it. `backend/main.py` is the single Uvicorn entry point for catalogue, authentication, and chat. Use a production deployment with HTTPS, secure session tokens, rate limiting, and a managed secrets store before exposing authentication publicly.
