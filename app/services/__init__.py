"""Application service layer.

API routes will delegate here; workers reuse these services. Keep HTTP handling,
vendor SDKs, database queries and hardware-specific settings in their own layers.
These modules define responsibilities only; implementations and wiring are pending.
"""
