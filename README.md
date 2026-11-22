# AI PDF Chatbot

A portfolio project with production-oriented architecture: upload private PDFs, ask questions, and receive grounded answers with page citations.

**Stage:** FastAPI shell and Docker scaffolding. PDF/model/storage/worker/UI business logic and real token verification are not implemented yet.

## Documentation

Read these four documents in order:

| Document | Owns |
| --- | --- |
| [PRD](docs/PRD.md) | Product scope, behavior and acceptance criteria. |
| [Technical design](docs/TECHNICAL_DESIGN.md) | Architecture, contracts, local/GPU portability, security and capacity. |
| [Technology stack](docs/TECH_STACK.md) | Selected technologies and supporting tools. |
| [Implementation plan](docs/IMPLEMENTATION_PLAN.md) | Ordered development tasks, tests and completion checks. |

Local development does not require a dedicated GPU. Use deterministic tests and optional real CPU/native Ollama inference. Later staging/production uses GPU-backed Ollama with the same application contracts; endpoint, credentials, resource and infrastructure settings change. Normal hardware migration must not require rewriting business logic.

The future 1,000–5,000 requests/second objective is **unverified**. Local implementation, deployment configuration and measured production capacity are separate achievements. Never present fake-model tests as semantic accuracy or target-rate proof.

Setup/test commands will be added when their implementation exists. Commit only permitted fixtures and safe configuration examples; keep uploaded PDFs, credentials, model files, databases and private logs out of Git.

## Configuration

Copy `.env.example` to `.env` before using Compose, then replace `POSTGRES_PASSWORD`, `REDIS_PASSWORD` and `RABBITMQ_PASSWORD` with distinct private local values. Use letters, digits, `_` and `-` to keep the generated connection URLs valid. `.env` is ignored by Git; never commit it.

- **Addresses:** containers use service names (`postgres:5432`, `redis:6379`, `rabbitmq:5672`, `chroma:8000`); host tools use the published localhost ports (Chroma defaults to `localhost:8001`). Container `localhost` is not your laptop.
- **Model settings are planned application contracts:** `MODEL_BACKEND=fake` selects deterministic development behavior once implemented; use `ollama` for real inference. Model adapters and document/chat business logic are not implemented yet.
- **Ollama endpoints:** `OLLAMA_GENERATION_URL`, `OLLAMA_QUERY_EMBEDDING_URL` and `OLLAMA_INGESTION_EMBEDDING_URL` default to `http://host.docker.internal:11434` for native host Ollama. For CPU Ollama in Compose, set all three to `http://ollama:11434` and enable `models`. A host-run client instead reaches native Ollama through `http://localhost:11434`.
- **Optional services:** enable only the profiles listed below. Image (`*_IMAGE`) and host-port (`*_PORT`) overrides are listed in `.env.example`; changing a host port does not change the internal service address.
- **Later GPU/production:** change private endpoints, secrets, resource settings and the applicable deployment override; keep domain logic unchanged. The NVIDIA override below requires compatible Linux hardware and is not a production-ready deployment by itself.

## Local Docker setup

Install/start [Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/). Then:

```bash
cp .env.example .env
# Edit .env and replace the three example passwords before starting services.
docker compose config --quiet
docker compose up -d
```

The default starts **PostgreSQL + Redis**. All published ports bind to localhost and service data uses named volumes. Optional profiles keep the laptop footprint small:

| Profile | Service / use |
| --- | --- |
| `jobs` | RabbitMQ, including its management UI on localhost:15672. |
| `vectors` | ChromaDB on localhost:8001. |
| `models` | CPU-only Ollama with persistent models; no automatic downloads. |
| `dev` | Non-root Python workspace using the shared image and mounted source. |
| `api` | FastAPI shell on localhost:8000; business services are not wired yet. |

```bash
docker compose --profile jobs --profile vectors up -d
docker compose --profile dev run --build --rm workspace bash
```

The Python image installs the current requirements snapshot, including test tools, and now starts the FastAPI shell by default. UI and worker commands will be added when their implementations exist. Chroma, object-storage and OIDC integration checks will be added with their implementation; object-store and identity-provider containers are not included yet.

For the configured CPU model service, run `docker compose --profile models up -d ollama`, then download models with `docker compose exec ollama ollama pull qwen3:4b` and the same command for `nomic-embed-text`. Do not run host and container Ollama on the same published port.

`compose.gpu.yaml` is an optional NVIDIA/Linux override for later hardware: `docker compose -f compose.yaml -f compose.gpu.yaml --profile models up -d ollama`. It requires a working GPU/driver/container toolkit and is not for this Mac. No application code changes are needed just to select GPU devices.

`docker compose down` preserves named data volumes. Initial database/broker credentials are persisted in those volumes; changing `.env` later does not automatically rotate them. Real `.env` files, local virtual environments, private data and model files are excluded from Git/image builds. Image digests are pinned; overrides are explicit environment settings. This is local development scaffolding, not a production deployment or a throughput claim.

## API shell

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
# In another terminal:
.venv/bin/python -m pytest -q
```

Development documentation: [Swagger UI](http://127.0.0.1:8000/docs). Liveness is `GET /health/live`; readiness intentionally returns `503` until service initialization is implemented. Versioned routes under `/api/v1` cover uploads, documents, chat, jobs and capabilities, with typed schemas and a common error envelope/request ID.

All data routes fail closed: no Bearer token returns `401`; token verification is not wired, so an arbitrary Bearer token returns `503`, never user access. Route shells return `501` after authentication is replaced in isolated tests. No jobs, documents, model answers or database writes are fabricated. This shell is not production-ready authentication or storage integration.

Docker alternative: `docker compose --profile api up --build -d api` exposes the same shell on localhost:8000. It starts without database/model connections and does not claim readiness. Interactive docs are disabled when `APP_ENV=production`; use real production validation before any deployment.
