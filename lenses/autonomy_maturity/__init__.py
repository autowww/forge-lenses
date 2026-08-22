"""Autonomy maturity assessment — observed level/grade, 0-100 score, recommendations.

Canonical spec: Blueprints ``AUTONOMY-MATURITY-FRAMEWORK.md``. Scores are
observed from repo signals (never Wizard session intent).
"""

from lenses.autonomy_maturity.aggregate import (
    build_overview_payload,
    build_project_payload,
)
from lenses.autonomy_maturity.feature_flag import experimental_autonomy_maturity_enabled

__all__ = [
    "build_overview_payload",
    "build_project_payload",
    "experimental_autonomy_maturity_enabled",
]
