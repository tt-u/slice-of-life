from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Role = str
ActionTag = Literal["public", "private", "finance", "legal", "delay"]
WinTier = Literal["decisive_win", "scrappy_win", "pyrrhic_win", "loss"]


@dataclass(frozen=True, slots=True)
class SeedEntity:
    id: str
    name: str
    role: Role
    public_goal: str
    pressure_point: str
    starting_trust: int
    influence: int
    stance: str
    details: str


@dataclass(frozen=True, slots=True)
class AgentProfile:
    id: str
    name: str
    role: Role
    public_goal: str
    private_fear: str
    pressure_point: str
    voice: str
    stance: str
    trust_in_player: int
    influence: int
    source_seed_id: str


@dataclass(frozen=True, slots=True)
class ActionCard:
    id: str
    label: str
    description: str
    tag: ActionTag
    public_pressure: int = 0
    narrative_shift: int = 0
    exchange_shift: int = 0
    liquidity_shift: int = 0
    treasury_shift: int = 0
    control_shift: int = 0
    volatility_shift: int = 0
    kol_trust_shift: int = 0
    whale_trust_shift: int = 0
    exchange_trust_shift: int = 0
    unlocks_truth: bool = False


@dataclass(slots=True)
class WorldState:
    turn_index: int = 0
    turns_total: int = 6
    credibility: int = 52
    treasury: int = 58
    pressure: int = 38
    price: int = 43
    liquidity: int = 46
    sell_pressure: int = 67
    volatility: int = 70
    community_panic: int = 72
    rumor_level: int = 66
    narrative_control: int = 34
    exchange_trust: int = 44
    control: int = 53
    truth_public: bool = False
    flags: set[str] = field(default_factory=set)

    def clamp(self) -> None:
        for field_name in (
            "credibility",
            "treasury",
            "pressure",
            "price",
            "liquidity",
            "sell_pressure",
            "volatility",
            "community_panic",
            "rumor_level",
            "narrative_control",
            "exchange_trust",
            "control",
        ):
            value = getattr(self, field_name)
            setattr(self, field_name, max(0, min(100, value)))


@dataclass(frozen=True, slots=True)
class TurnChoice:
    action: ActionCard
    reason: str


@dataclass(frozen=True, slots=True)
class WorldEvent:
    headline: str
    summary: str
    severity: int
    actor_id: str = "system"
    actor_name: str = "System"
    state_delta: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AgentReaction:
    actor_id: str
    actor_name: str
    role: Role
    summary: str
    stance: str
    trust_after: int
    state_delta: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TurnResolution:
    turn_number: int
    action_id: str
    action_label: str
    narrative: str
    bullet_points: tuple[str, ...]
    state_snapshot: WorldState
    pre_turn_event: WorldEvent | None = None
    agent_reactions: tuple[AgentReaction, ...] = ()


@dataclass(frozen=True, slots=True)
class WorldReport:
    initial_state: dict[str, int]
    final_state: dict[str, int]
    diff: dict[str, int]
    summary: str
    share_text: str
    timeline_markdown: str
    ending_score: int
    ending_id: str
    ending_title: str
    ending_description: str


@dataclass(frozen=True, slots=True)
class InitialWorldValidation:
    is_playable: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ScenarioBlueprint:
    title: str
    premise: str
    player_role: str
    player_secret: str
    objective: str
    opponent: str
    audience: tuple[str, ...]
    truth: str
    opening_event: WorldEvent
    entities: tuple[SeedEntity, ...]
    initial_world: WorldState
    playable_roles: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ScenarioDefinition:
    id: str
    title: str
    premise: str
    player_role: str
    player_secret: str
    objective: str
    opponent: str
    audience: tuple[str, ...]
    truth: str
    opening_event: WorldEvent
    seed_entities: tuple[SeedEntity, ...]
    actions: tuple[ActionCard, ...]
    initial_world: WorldState
    playable_roles: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ScenarioViewpointCard:
    role: str
    summary: str
    metrics: dict[str, int]
    metric_deltas: dict[str, int]
    delta_summary: str
    contrast_score: int
    focus_metrics: tuple[str, ...]
    key_entities: tuple[str, ...]
    player_entity: str
    player_entity_role: str
    primary_counterpart: str
    primary_counterpart_role: str
    player_entity_resolved: bool = True
    primary_counterpart_resolved: bool = True
    relationship_summary: str = ""
    opening_headline: str = ""
    is_selected: bool = False
    is_baseline: bool = False


@dataclass(frozen=True, slots=True)
class ScenarioRoleOverviewCard:
    role: str
    metrics: dict[str, int]
    summary: str
    relationship_summary: str
    delta_summary: str
    contrast_score: int
    focus_metrics: tuple[str, ...]
    primary_counterpart: str = ""
    primary_counterpart_role: str = ""
    player_entity_resolved: bool = True
    primary_counterpart_resolved: bool = True
    is_selected: bool = False
    is_baseline: bool = False
    is_comparison: bool = False


@dataclass(frozen=True, slots=True)
class ScenarioRoleComparisonCard:
    reference_role: str
    reference_summary: str
    reference_metrics: dict[str, int]
    reference_relationship_summary: str
    compared_role: str
    compared_summary: str
    compared_metrics: dict[str, int]
    metric_deltas: dict[str, int]
    delta_summary: str
    contrast_score: int
    focus_metrics: tuple[str, ...]
    compared_relationship_summary: str
    is_primary: bool = False


@dataclass(frozen=True, slots=True)
class MaterialSeedInspection:
    title: str
    playable_roles: tuple[str, ...]
    selected_role: str | None
    baseline_role: str
    baseline_summary: str
    selected_summary: str = ""
    comparison_summary: str = ""
    role_overview: tuple[str, ...] = ()
    role_overview_cards: tuple[ScenarioRoleOverviewCard, ...] = ()
    comparison_role: str | None = None
    comparison_focus: str = ""
    comparison_focus_metrics: tuple[str, ...] = ()
    comparison_focus_count: int = 0
    viewpoints: tuple[ScenarioViewpointCard, ...] = ()
    selected_viewpoint: ScenarioViewpointCard | None = None
    comparison_viewpoint: ScenarioViewpointCard | None = None
    selected_overview_card: ScenarioRoleOverviewCard | None = None
    comparison_overview_card: ScenarioRoleOverviewCard | None = None
    selected_role_comparisons: tuple[ScenarioRoleComparisonCard, ...] = ()
    primary_selected_role_comparison: ScenarioRoleComparisonCard | None = None
    pairwise_role_comparisons: tuple[ScenarioRoleComparisonCard, ...] = ()
