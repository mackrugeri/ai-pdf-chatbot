"""Staging and immutable accepted PDF storage.

Planned: bounded upload targets, checksum/version verification, immutable final
promotion and authorized downloads. Never accept a mutable latest key as the
identity of verified bytes; user filenames are display-only.
"""
