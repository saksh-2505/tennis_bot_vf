from observability.api import (
    get_platform_health,
    get_platform_metrics,
    get_recent_incidents,
    get_recent_telegram_diagnostics,
    get_service_health,
    get_trace_view,
    validate_match_pipeline,
    validate_named_pipeline,
    validate_platform_pipelines,
)
from observability.health._collectors import register_collector_health_checks
from observability.health._infrastructure import register_infrastructure_health_checks
from observability.health._services import register_service_health_checks
from observability.diagnostics._stages import register_pipeline_definitions

__all__ = [
    "get_platform_health",
    "get_service_health",
    "get_trace_view",
    "validate_platform_pipelines",
    "validate_named_pipeline",
    "validate_match_pipeline",
    "get_platform_metrics",
    "get_recent_incidents",
    "get_recent_telegram_diagnostics",
]


def initialize_observability() -> None:
    register_infrastructure_health_checks()
    register_collector_health_checks()
    register_service_health_checks()
    register_pipeline_definitions()
