"""Attempt-isolated vector writes, retrieval and cleanup.

Planned: owner/document/version/attempt filters, bounded upserts and verified
chunk counts. Retrieve only published attempts; loser cleanup cannot delete
winning records. Convert provider records into application-owned types.
"""
