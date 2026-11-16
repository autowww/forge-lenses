"""Resolve repository branch strategy for Branch Steward and Studio surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

BranchModel = Literal["team_tier", "forge_lanes"]
DocsHealthStyle = Literal["feature_prefixed", "legacy_docs_health"]

_BLUEPRINTS_BRANCHING = Path("blueprints") / "sdlc" / "methodologies" / "forge" / "setup" / "BRANCHING-STRATEGY.md"
_FORGE_BRANCHING_YML = Path("forge") / "branching.yml"
_FORGE_CONFIG_YAML = Path("forge") / "forge.config.yaml"
_DOCS_PROCESS_PROFILE = Path("docs") / "process" / "branching-profile.md"


@dataclass(frozen=True)
class BranchStewardPolicy:
    trunk: str
    model: BranchModel
    source: str
    team_scale: str
    topology: str
    cicd_maturity: str
    feature_prefix: str
    fix_prefix: str
    product_prefix: str
    iter_prefix: str
    spark_prefix: str
    spike_prefix: str
    release_prefix: str
    hotfix_prefix: str
    require_pr: bool
    required_approvals: int
    require_green_checks: bool
    docs_health_style: DocsHealthStyle
    raw: dict[str, Any]

    @property
    def lanes_enabled(self) -> bool:
        return self.model == "forge_lanes"

    def recommendations(self) -> dict[str, str]:
        """Small operator-facing recommendations for common task intents."""
        if self.model == "forge_lanes":
            return {
                "charge_work": f"{self.iter_prefix}<iteration-id> (or lane specified in forge/charge.md)",
                "backlog_lane_work": "use the task's existing lane parent; avoid mixing lanes in one branch",
                "ad_hoc_user_task": f"{self.iter_prefix}<iteration-id> (or {self.spark_prefix}<spark-id> for risky work)",
                "exploration_spike": f"{self.spike_prefix}<topic> (or isolated worktree)",
                "hotfix": f"{self.hotfix_prefix}<topic>",
                "release_hardening": f"{self.release_prefix}<version-or-rc> (only when policy requires)",
            }
        return {
            "charge_work": f"{self.feature_prefix}<topic> or {self.fix_prefix}<topic> depending on intent",
            "backlog_lane_work": "use branch documented by the backlog item when present",
            "ad_hoc_user_task": f"{self.feature_prefix}<topic> (or {self.fix_prefix}<topic> for bugfixes)",
            "exploration_spike": "prefer read-only exploration; use short-lived topic branch only when edits are needed",
            "hotfix": f"{self.fix_prefix}<topic> (or dedicated hotfix branch in production-sensitive repos)",
            "release_hardening": "normally merge to trunk; use release branch only if explicitly documented",
        }


def _read_yaml_dict(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        from yaml import safe_load  # noqa: PLC0415

        raw = path.read_text(encoding="utf-8", errors="replace")
        data = safe_load(raw)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _profile_mentions_lanes(profile_text: str) -> bool:
    t = profile_text.lower()
    return any(x in t for x in ("product/", "iter/", "spark/", "forge-native", "lane model"))


def _blueprints_strategy_exists(root: Path) -> bool:
    return (root / _BLUEPRINTS_BRANCHING).is_file()


def _booly(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return default


def _to_nonempty_str(value: Any, default: str) -> str:
    s = str(value or "").strip()
    return s if s else default


def _from_branching_yml(data: dict[str, Any]) -> BranchStewardPolicy:
    team = data.get("team") if isinstance(data.get("team"), dict) else {}
    lanes = data.get("lanes") if isinstance(data.get("lanes"), dict) else {}
    topic = data.get("topic_branches") if isinstance(data.get("topic_branches"), dict) else {}
    promo = data.get("promotion") if isinstance(data.get("promotion"), dict) else {}
    raw_model = str(data.get("model") or "").strip().lower()
    lanes_enabled = _booly(lanes.get("enabled")) or _booly(data.get("use_forge_lanes"))
    model: BranchModel = "forge_lanes" if raw_model == "forge_lanes" or lanes_enabled else "team_tier"

    style_raw = str(data.get("docs_health_branch_style") or data.get("docs_health_branches") or "").strip().lower()
    style: DocsHealthStyle = "legacy_docs_health" if style_raw in ("legacy", "docs-health", "docs_health") else "feature_prefixed"

    return BranchStewardPolicy(
        trunk=_to_nonempty_str(data.get("trunk") or data.get("default_branch"), "main"),
        model=model,
        source="forge/branching.yml",
        team_scale=_to_nonempty_str(team.get("scale"), "solo"),
        topology=_to_nonempty_str(team.get("topology"), "single"),
        cicd_maturity=_to_nonempty_str(team.get("cicd_maturity"), "none"),
        feature_prefix=_to_nonempty_str(topic.get("feature_prefix"), "feature/"),
        fix_prefix=_to_nonempty_str(topic.get("fix_prefix"), "fix/"),
        product_prefix=_to_nonempty_str(lanes.get("product_prefix"), "product/"),
        iter_prefix=_to_nonempty_str(lanes.get("default_iteration_prefix"), "iter/"),
        spark_prefix=_to_nonempty_str(lanes.get("spark_prefix"), "spark/"),
        spike_prefix=_to_nonempty_str(lanes.get("spike_prefix"), "spike/"),
        release_prefix=_to_nonempty_str(lanes.get("release_prefix"), "release/"),
        hotfix_prefix=_to_nonempty_str(lanes.get("hotfix_prefix"), "hotfix/"),
        require_pr=_booly(promo.get("require_pr"), default=True),
        required_approvals=int(promo.get("required_approvals") or 1),
        require_green_checks=_booly(promo.get("require_green_checks"), default=False),
        docs_health_style=style,
        raw=data,
    )


def _from_forge_config(data: dict[str, Any], source: str) -> BranchStewardPolicy:
    team = data.get("team") if isinstance(data.get("team"), dict) else {}
    scale = _to_nonempty_str(team.get("scale"), "solo")
    cicd_maturity = "standard"
    if scale == "solo":
        cicd_maturity = "none"
    return BranchStewardPolicy(
        trunk="main",
        model="team_tier",
        source=source,
        team_scale=scale,
        topology="single",
        cicd_maturity=cicd_maturity,
        feature_prefix="feature/",
        fix_prefix="fix/",
        product_prefix="product/",
        iter_prefix="iter/",
        spark_prefix="spark/",
        spike_prefix="spike/",
        release_prefix="release/",
        hotfix_prefix="hotfix/",
        require_pr=scale != "solo",
        required_approvals=1 if scale != "solo" else 0,
        require_green_checks=scale in ("team", "multi-team"),
        docs_health_style="feature_prefixed",
        raw=data,
    )


def _default_policy(source: str) -> BranchStewardPolicy:
    return BranchStewardPolicy(
        trunk="main",
        model="team_tier",
        source=source,
        team_scale="team",
        topology="single",
        cicd_maturity="standard",
        feature_prefix="feature/",
        fix_prefix="fix/",
        product_prefix="product/",
        iter_prefix="iter/",
        spark_prefix="spark/",
        spike_prefix="spike/",
        release_prefix="release/",
        hotfix_prefix="hotfix/",
        require_pr=True,
        required_approvals=1,
        require_green_checks=True,
        docs_health_style="feature_prefixed",
        raw={},
    )


def resolve_branch_steward_policy(project_root: Path, workspace_root: Path | None = None) -> BranchStewardPolicy:
    """Resolve branch policy for one project root."""
    pr = project_root.resolve()
    branch_yml = _read_yaml_dict(pr / _FORGE_BRANCHING_YML)
    if branch_yml:
        return _from_branching_yml(branch_yml)

    profile_path = pr / _DOCS_PROCESS_PROFILE
    if profile_path.is_file():
        if _profile_mentions_lanes(_read_text(profile_path)):
            d = _default_policy("docs/process/branching-profile.md")
            return BranchStewardPolicy(**{**d.__dict__, "model": "forge_lanes"})

    forge_cfg = _read_yaml_dict(pr / _FORGE_CONFIG_YAML)
    if forge_cfg:
        return _from_forge_config(forge_cfg, "forge/forge.config.yaml")

    if _blueprints_strategy_exists(pr):
        return _default_policy("blueprints/…/BRANCHING-STRATEGY.md")

    if workspace_root is not None and _blueprints_strategy_exists(workspace_root.resolve()):
        return _default_policy("workspace/blueprints/…/BRANCHING-STRATEGY.md")

    return _default_policy("fallback_team_tier")


def categorize_branch_name(name: str) -> str:
    n = (name or "").strip()
    if not n:
        return "other"
    if n == "main":
        return "main"
    prefixes = (
        ("product/", "product"),
        ("iter/", "iter"),
        ("spark/", "spark"),
        ("spike/", "spike"),
        ("release/", "release"),
        ("hotfix/", "hotfix"),
        ("feature/", "feature"),
        ("fix/", "fix"),
        ("topic/", "topic"),
    )
    for pref, label in prefixes:
        if n.startswith(pref):
            return label
    return "other"
