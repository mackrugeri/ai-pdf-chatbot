"""Durable job lifecycle and discovery.

Planned: owner-scoped job creation/list/detail/cancellation, idempotency receipts,
transactional outbox, leases, deadlines, retry/recovery and result retention.
Broker transport belongs in adapters; workers invoke services rather than routes.
"""
