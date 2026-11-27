# AI PDF Chatbot

A portfolio project with production-oriented architecture: upload private PDFs, ask questions, and receive grounded answers with page citations.

**Stage:** Streamlit UI for login, upload, documents, chat, and jobs is implemented. PostgreSQL, OIDC, and API auth are wired; document/chat business operations, model execution, workers, and object storage remain incomplete.

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

The PostgreSQL pool, versioned migrations, local OIDC authentication and protected API boundary are implemented. Document/chat business operations, model execution, workers and storage remain scaffolds. Keep uploaded PDFs, credentials, model files, databases and private logs out of Git.

## Configuration

Copy `.env.example` to `.env` before using Compose, then replace `POSTGRES_PASSWORD`, `REDIS_PASSWORD` and `RABBITMQ_PASSWORD` with distinct private local values. Use letters, digits, `_` and `-` to keep the generated connection URLs valid. `.env` is ignored by Git; never commit it.

- **Addresses:** containers use service names (`postgres:5432`, `redis:6379`, `rabbitmq:5672`, `chroma:8000`); host tools use the published localhost ports (Chroma defaults to `localhost:8001`). Container `localhost` is not your laptop.
- **Model settings:** `MODEL_BACKEND=fake` selects the future deterministic development adapter; use `ollama` for real inference. Model adapters and document/chat business logic are not implemented yet.
- **Ollama endpoints:** Host-run `OLLAMA_GENERATION_URL`, `OLLAMA_QUERY_EMBEDDING_URL` and `OLLAMA_INGESTION_EMBEDDING_URL` use `http://localhost:11434`. Compose uses the corresponding `DOCKER_OLLAMA_*` overrides, defaulting to `http://host.docker.internal:11434`; set those three to `http://ollama:11434` for the `models` profile. The application receives the same generic settings in either environment.
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
| `auth` | Local Keycloak realm and demo user on localhost:8080. The `api` profile starts it as a dependency. |
| `api` | FastAPI on localhost:8000; protected business operations remain scaffolds. |

```bash
docker compose --profile jobs --profile vectors --profile auth up -d
# Copy the Streamlit auth example and set its cookie/client secrets:
mkdir -p .streamlit
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Use the same client secret as KEYCLOAK_STREAMLIT_CLIENT_SECRET in .env.
# In a second terminal, from the project virtual environment:
source .venv/bin/activate
python -m app.storage.postgres.migrate
docker compose --profile dev run --build --rm workspace bash
```

The Python image installs the current requirements snapshot, including test tools, and starts the FastAPI shell by default. Run the Streamlit UI on the host as described below; worker commands will be added when their implementation exists. Chroma and object-storage integration checks will be added with their implementation. Keycloak is a local development identity provider only; its `start-dev` mode and bundled demo account are never for production.

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

Development documentation: [Swagger UI](http://127.0.0.1:8000/docs). Liveness is `GET /health/live`; readiness returns `200` only when PostgreSQL is reachable and the migration ledger exists. Run migrations explicitly before starting the API; migrations are never applied implicitly at API startup. Versioned routes under `/api/v1` cover uploads, documents, chat, jobs and capabilities, with typed schemas and a common error envelope/request ID.

All `/api/v1` routes require a Bearer access token with the `pdf-api` audience. FastAPI independently validates the configured issuer, signature, asymmetric algorithm, expiry, issuer, audience and required claims against cached JWKS. Unknown signing keys trigger a bounded refresh for key rotation; identity-provider outages fail closed with `503`. The API maps `(issuer, subject)` to PostgreSQL and rejects inactive users. `pdf:read` and `pdf:write` roles are enforced per route. The API business handlers still return `501`, so UI workflows need the remaining backend implementation before real PDFs/jobs can be processed.

Docker alternative: after starting PostgreSQL and running migrations, `docker compose --profile api up --build -d api` exposes the shell on localhost:8000. The API opens a bounded PostgreSQL pool at startup and fails startup if PostgreSQL is configured but unavailable. Real-model execution, queues, and storage integrations remain incomplete. Interactive docs are disabled when `APP_ENV=production`; use real production validation before any deployment.

Configuration code lives in `app/config/`; `from app.config import Settings` remains the application entry point. Component settings load `.env`, with process environment overriding it. Connection secrets are masked in representations/JSON; validation errors hide inputs. Production requires HTTPS OIDC issuer/JWKS endpoints and an explicit API audience. Validation does not establish connectivity. Never log raw secrets, access tokens or unredacted validation error dictionaries.

| Configuration module | Owns |
| --- | --- |
| `app/config/database.py` | Secret PostgreSQL URL, bounded pool/connect timeouts. |
| `app/config/broker.py` | Secret RabbitMQ URL, distinct queues, bounded retries/prefetch. |
| `app/config/redis.py` | Secret Redis URL, database index, bounded connections/timeouts. |
| `app/config/models.py` | Fake/Ollama mode, model identities, separate endpoints, context/output/concurrency budgets. |
| `app/config/auth.py` | Issuer/audience/JWKS, asymmetric algorithm allowlist, timeout/cache/skew limits. |
| `app/config/chroma.py` | Host/port/TLS, tenant/database, optional gateway token. |
| `app/config/object_storage.py` | Object/journal endpoints, buckets, paired secret keys, signed-URL expiry and independence declaration. |

Blank optional `.env` values are ignored for local scaffolding. Production validation requires configured database/broker/Redis, real model mode, HTTPS OIDC, Chroma host, and HTTPS object/journal endpoints with an independent journal declaration. A declaration cannot prove account/retention isolation; verify it when provisioning. Explicit storage key pairs are optional for future SDK workload identity. Settings perform no network calls. The API manages PostgreSQL lifecycle/readiness and OIDC authentication; workers, object storage and business operations remain incomplete.

### PostgreSQL schema

`python -m app.storage.postgres.migrate` applies ordered SQL migrations under a PostgreSQL advisory lock. It records SHA-256 checksums, refuses changed or missing applied migrations, and applies each migration in a transaction. Add a new numbered migration for schema changes; never edit an applied migration. The API does not run DDL on startup. `DB_POOL_MIN_SIZE`, `DB_POOL_MAX_SIZE`, `DB_CONNECT_TIMEOUT_SECONDS` and `DB_POOL_TIMEOUT_SECONDS` bound each API process pool; deployment must budget the sum across all API replicas against the database connection limit. The current default pool is a development baseline, not a 1,000–5,000 RPS capacity claim.

### Local authentication

The `auth` Compose profile starts Keycloak in development mode and imports [`auth/ai-pdf-chatbot-realm.json`](auth/ai-pdf-chatbot-realm.json). The realm provisions a confidential Streamlit OIDC client, the `pdf-api` audience, `pdf:read`/`pdf:write` roles and a `demo` user. Set separate local-only Keycloak admin, client and demo passwords in `.env`; copy `.streamlit/secrets.toml.example` and use the same Streamlit client secret there. Generate a private Streamlit cookie secret (for example, `python -c "import secrets; print(secrets.token_urlsafe(48))"`). Never commit `.streamlit/secrets.toml`. The imported realm is applied only when Keycloak first creates it; later realm edits require updating it through the local admin console or a deliberately reset local Keycloak data volume.

Run the UI with `streamlit run ui/app.py`. Streamlit performs OIDC Authorization Code login, exposes only the access token required for API calls, and logs out through `st.logout()`. The token remains in Streamlit's auth session and is not displayed, logged, or copied to app session state. The API—not the UI—validates the token and derives ownership from the verified `sub`; client-provided owner IDs are never trusted. A 401 in the UI prompts reauthentication. For local development, `.env` uses `localhost` as the token issuer; the API container reaches JWKS through the internal `keycloak` service address.

## Streamlit UI

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`, set the private cookie secret and match `client_secret` to `KEYCLOAK_STREAMLIT_CLIENT_SECRET` in `.env`. Start local PostgreSQL, apply migrations, and start Keycloak with `docker compose --profile auth up -d keycloak`. Start the API with `docker compose --profile api up --build -d api`, then run `streamlit run ui/app.py` from the project virtual environment.

The UI provides PDF signature/size validation and presigned upload transfer, owner-scoped document status/pagination, multi-document questions with job status and page/source excerpts, job filtering/history/cancellation, failed-ingestion retry, and confirmation-gated deletion. The access token is sent only to FastAPI; signed upload targets use a separate HTTP client without the Bearer header. UI error text, filenames, model answers, and excerpts are rendered as plain text. App-held cursor, job, and widget state is cleared on logout or reauthentication.

The upload screen sends its file and the other screens call their documented `/api/v1` operations. Those backend operations currently return `501`; this is a visible API capability boundary, not an end-to-end functioning chatbot yet. The UI uses explicit refresh actions for job status and does not claim that upload, ingestion, retrieval, answer generation, retry, or deletion has completed until the API returns those results.
