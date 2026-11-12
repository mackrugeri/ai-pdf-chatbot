# AI PDF Chatbot

A portfolio project with production-oriented architecture: upload private PDFs, ask questions, and receive grounded answers with page citations.

**Stage:** documentation and planning. Application code, services, model runs and deployment are not implemented or verified by these documents.

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
