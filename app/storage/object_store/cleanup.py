"""Version-aware object retention and physical cleanup.

Planned: remove applicable object versions, noncurrent versions, orphan attempts
and multipart remnants through bounded retries. A delete marker is not physical
erasure. Do not remove active inputs or journal entries before their retention.
"""
