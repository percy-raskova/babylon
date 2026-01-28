"""Integration tests for Marxian value tensors with real QCEW data.

This package contains empirical validation tests that verify hydrated tensors
match real-world economic data from the Bureau of Labor Statistics' Quarterly
Census of Employment and Wages (QCEW) program.

Test Categories:
    - Accounting identity: allocated_v + excluded = QCEW total
    - Piketty guardrails: Profit rates within historical 3-8% bounds
    - Detroit gentrification signal: Oakland IIb/IIa > Wayne IIb/IIa
    - Temporal consistency: YoY changes ≤30%
    - Out-of-sample prediction: Train 2010-2019, test 2020-2022

These tests require the QCEW database to be present and will skip gracefully
if the database is not found.
"""
