"""Provider-neutral storage failures.

Planned: distinguish unavailable, conflict, missing, integrity and retryable
failures. Translate SDK/database exceptions without exposing credentials,
queries, object URLs or private document contents.
"""
