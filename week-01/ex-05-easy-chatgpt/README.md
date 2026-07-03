# Easy ChatGPT

Week 1, Exercise 5 project scaffold.

## Structure

- `backend/` — FastAPI application
- `frontend/` — vanilla HTML, CSS, and JavaScript
- `docker-compose.yml` — local service orchestration

## Run

Copy `.env.example` to `.env`, then start the services:

```sh
docker compose up --build
```

- Frontend: http://localhost:8080
- Backend: http://localhost:8000

Chat, streaming, and vision features are intentionally not implemented yet.
