"""Database deletion and audit metadata.

Planned: tombstones, cleanup status and minimal audit records. This database
repository is not the independent recovery journal; its contract lives under
object_store/journal.py and must survive application database rollback.
"""
