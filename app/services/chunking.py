"""Deterministic page-aware text chunking.

Planned: bounded overlapping chunks, guaranteed forward progress and stable source
metadata. Keep page boundaries and version the chunking configuration.
This module should remain independent of storage and model providers.
"""
