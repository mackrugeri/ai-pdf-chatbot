"""Encrypted job input, result and attempt artifact objects.

Planned: immutable scoped references, ownership-safe reads and orphan cleanup.
Retain active inputs through recovery grace; expire terminal results without
erasing independent idempotency receipts.
"""
