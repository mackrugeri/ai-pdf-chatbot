"""Idempotency receipt repository.

Planned: owner/endpoint/key uniqueness, request hashes and retained job references.
Expired payloads must not turn retries into new jobs.
"""
