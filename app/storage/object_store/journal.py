"""Independent deletion recovery journal adapter.

Planned: durable idempotent minimal intents, protected append-only history and
verified replay/checkpoint coverage. Production must place this journal outside
the application database restore boundary; a local bucket only simulates it.
"""
