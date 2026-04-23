"""Incident and ops signal adapters."""

from lenses.ops_delivery.adapters.incident_generic import normalize_generic_incident
from lenses.ops_delivery.adapters.incident_pagerduty import normalize_pagerduty_incident

__all__ = ["normalize_generic_incident", "normalize_pagerduty_incident"]
