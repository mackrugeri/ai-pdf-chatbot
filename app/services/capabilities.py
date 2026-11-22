"""Service readiness and capability reporting.

Planned: aggregate initialized dependency/schema/model availability and configured
limits without expensive generation probes or exposing secrets.
Do not claim readiness until real initialization and checks exist.
"""
