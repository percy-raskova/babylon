"""Integration tests for data loaders.

Tests for:
- Idempotency (DELETE+INSERT pattern verification)
- ETL pitfalls (NULL handling, type coercion, batching)
- Loader contracts (all loaders implement DataLoader interface)
"""
