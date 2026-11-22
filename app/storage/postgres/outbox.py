"""Transactional outbox repository.

Planned: persist events with job changes and track confirmed publication/retries.
Broker transport belongs in adapters; duplicate delivery remains possible.
"""
