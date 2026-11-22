"""Embedding orchestration and scheduling.

Planned: bounded batches, model/dimension fingerprint checks, no silent truncation,
and separate query versus ingestion budgets. Local operation can serialize work.
Use model adapter interfaces rather than CPU/GPU-specific logic.
"""
