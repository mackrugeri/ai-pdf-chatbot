"""PostgreSQL connections and transaction boundaries.

Planned: bounded Psycopg pools, explicit startup/shutdown and transaction contexts.
Use parameterized queries; never hold transactions across model/storage calls.
Schema changes belong in the root migrations directory.
"""
