"""CI/CD provider normalizers (dict in → canonical pipeline_run / deployment row)."""

from lenses.cicd_orchestration.adapters.argo_cd import normalize_argo_application_sync
from lenses.cicd_orchestration.adapters.azure_pipelines import normalize_azure_pipeline_run
from lenses.cicd_orchestration.adapters.github_actions import normalize_github_actions_run
from lenses.cicd_orchestration.adapters.gitlab_ci import normalize_gitlab_ci_pipeline
from lenses.cicd_orchestration.adapters.jenkins import normalize_jenkins_build

__all__ = [
    "normalize_argo_application_sync",
    "normalize_azure_pipeline_run",
    "normalize_github_actions_run",
    "normalize_gitlab_ci_pipeline",
    "normalize_jenkins_build",
]
