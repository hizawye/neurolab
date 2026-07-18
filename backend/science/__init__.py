"""Scientific validation harness.

Separate from `backend.modules`, which serves the API. Nothing here runs in a
request path: this package builds benchmark datasets and measures whether a
scoring method actually predicts anything.
"""
