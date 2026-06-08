"""datathink load-simulation harness.

Two tiers (see README.md):

  * ``driver.py``  — realistic multi-virtual-user load harness (off-CI). Drives a
    running server over HTTP with weighted, session-cookie-bearing user journeys,
    a stepped ramp to find the knee, latency percentiles, error-rate, a
    head-of-line-blocking probe, and optional resource sampling.
  * ``scenarios.py`` — the weighted user journeys the driver replays.

The fast, CI-runnable in-process concurrency test lives in
``backend/tests/test_concurrency_smoke.py`` (added with the head-of-line fix).
"""
