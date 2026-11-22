"""Durable document indexing workflow.

Planned: coordinate extraction, chunking and embeddings under job leases. Write
attempt-isolated vectors/artifacts and publish only a verified winning attempt.
Loser cleanup must never modify winning records; retries remain idempotent.
"""
