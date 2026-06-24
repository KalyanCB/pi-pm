"""Fundamental Intelligence Layer (ADR-039).

A standalone subsystem that ingests company/sector news, extracts structured
catalysts with an AI model, and maintains a watch list of active catalysts.

NOT yet wired into the recommendation engine or daily batch — that integration is
a separate, later change. Importing this package has no effect on the trading flow.
"""
