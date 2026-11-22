"""Journal-protected deletion and cleanup.

Planned: durable independent deletion intents, database tombstones, cancellation,
scoped vector/object-version/result cleanup and restore replay gates.
Exclude accepted deletions immediately; reconcile partial failures safely.
"""
