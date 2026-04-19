from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal

Role = str
ActionTag = Literal["public", "private", "finance", "legal", "delay"]
WinTier = Literal["decisive_win", "scrappy_win", "pyrrhic_win", "loss"]
WorldDimensionHealth = Literal["higher_is_better", "lower_is_better", "balanced"]

WORLD_STATE_DIMENSION_KEYS = (
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
)


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
        for field_name in WORLD_STATE_DIMENSION_KEYS:
            value = getattr(self, field_name)
            setattr(self, field_name, max(0, min(100, value)))

    def to_dimension_map(self) -> dict[str, int]:
        return {field_name: int(getattr(self, field_name)) for field_name in WORLD_STATE_DIMENSION_KEYS}


@dataclass(frozen=True, slots=True)
class WorldDimensionDef:
    key: str
    label: str
    description: str
    direction_of_health: WorldDimensionHealth
    warning_threshold: int | None = None
    crisis_threshold: int | None = None
    terminal_threshold: int | None = None


@dataclass(frozen=True, slots=True)
class ActionCostType:
    key: str
    label: str
    description: str


@dataclass(frozen=True, slots=True)
class ActionGenerationRule:
    key: str
    label: str
    description: str
    trigger_dimensions: tuple[str, ...]
    preferred_upside_dimensions: tuple[str, ...]
    likely_downside_dimensions: tuple[str, ...]
    allowed_cost_types: tuple[str, ...]
    minimum_upside_count: int = 1
    minimum_downside_count: int = 1
    max_upside_count: int = 2
    max_downside_count: int = 2
    intensity_range: tuple[int, int] = (1, 3)
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WorldActionGrammar:
    rules: tuple[ActionGenerationRule, ...]
    cost_types: tuple[ActionCostType, ...]
    forbidden_pairs: tuple[tuple[str, str], ...] = ()
    forbidden_tags: tuple[str, ...] = ()
    required_tradeoff: bool = True
    menu_size: int = 4
    low_commitment_slots: int = 1
    medium_commitment_slots: int = 2
    high_commitment_slots: int = 1


@dataclass(frozen=True, slots=True)
class TurnSituation:
    turn_index: int
    turns_total: int
    selected_player_role: str
    objective: str
    dominant_tensions: tuple[str, ...]
    urgent_dimensions: tuple[str, ...]
    unstable_dimensions: tuple[str, ...]
    recent_action_summaries: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ActionGenerationContext:
    world_title: str
    player_role: str
    dimensions: dict[str, int]
    dimension_defs: tuple[WorldDimensionDef, ...]
    situation: TurnSituation
    action_grammar: WorldActionGrammar


@dataclass(frozen=True, slots=True)
class GeneratedAction:
    id: str
    label: str
    description: str
    rationale: str
    upside_dimensions: tuple[str, ...]
    downside_dimensions: tuple[str, ...]
    upside_magnitude: dict[str, int]
    downside_magnitude: dict[str, int]
    cost_types: tuple[str, ...]
    affected_entities: tuple[str, ...]
    commitment_tier: Literal["low", "medium", "high"]
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WorldEndingBand:
    min_score: int
    ending_id: str
    label: str
    description: str


@dataclass(frozen=True, slots=True)
class MaterialResearchPack:
    case_id: str
    title: str
    source_material: str
    premise: str
    opponent: str
    audience: tuple[str, ...]
    truth: str
    entities: tuple[SeedEntity, ...]
    candidate_viewpoints: tuple[str, ...]
    opening_event: "WorldEvent"
    research_notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FrozenInitialWorld:
    world_id: str
    title: str
    premise: str
    player_role: str
    player_secret: str
    objective: str
    opponent: str
    audience: tuple[str, ...]
    truth: str
    selectable_roles: tuple[str, ...]
    allowed_turn_counts: tuple[int, ...]
    opening_event: "WorldEvent"
    initial_dimensions: tuple[tuple[str, int], ...]
    entities: tuple[SeedEntity, ...]
    ending_bands: tuple[WorldEndingBand, ...]
    dimension_defs: tuple[WorldDimensionDef, ...] = ()
    action_grammar: WorldActionGrammar | None = None

    def initial_dimension_map(self) -> dict[str, int]:
        return {key: value for key, value in self.initial_dimensions}

    def resolved_dimension_defs(self) -> tuple[WorldDimensionDef, ...]:
        return self.dimension_defs or default_world_dimension_defs(self.initial_dimension_map())

    def instantiate_state(self, *, turns_total: int) -> WorldState:
        dimension_map = self.initial_dimension_map()
        return WorldState(
            turn_index=0,
            turns_total=turns_total,
            credibility=dimension_map["credibility"],
            treasury=dimension_map["treasury"],
            pressure=dimension_map["pressure"],
            price=dimension_map["price"],
            liquidity=dimension_map["liquidity"],
            sell_pressure=dimension_map["sell_pressure"],
            volatility=dimension_map["volatility"],
            community_panic=dimension_map["community_panic"],
            rumor_level=dimension_map["rumor_level"],
            narrative_control=dimension_map["narrative_control"],
            exchange_trust=dimension_map["exchange_trust"],
            control=dimension_map["control"],
            truth_public=False,
            flags=set(),
        )

    def resolve_ending_band(self, ending_score: int) -> WorldEndingBand:
        score = max(0, min(100, ending_score))
        ordered = sorted(self.ending_bands, key=lambda band: band.min_score, reverse=True)
        return next(band for band in ordered if score >= band.min_score)

    def build_action_generation_context(self, *, state: WorldState, situation: TurnSituation) -> ActionGenerationContext:
        dimensions = state.to_dimension_map()
        dimension_defs = self.resolved_dimension_defs()
        resolved_situation = replace(
            situation,
            urgent_dimensions=situation.urgent_dimensions or infer_urgent_dimensions(dimensions, dimension_defs),
            unstable_dimensions=situation.unstable_dimensions or infer_unstable_dimensions(dimensions, dimension_defs),
        )
        return ActionGenerationContext(
            world_title=self.title,
            player_role=resolved_situation.selected_player_role,
            dimensions=dimensions,
            dimension_defs=dimension_defs,
            situation=resolved_situation,
            action_grammar=self.action_grammar or default_world_action_grammar(()),
        )


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

    def selectable_roles(self) -> tuple[str, ...]:
        return self.playable_roles or (self.player_role,)

    def to_material_research_pack(
        self,
        *,
        source_material: str,
        research_notes: tuple[str, ...] = (),
    ) -> MaterialResearchPack:
        return MaterialResearchPack(
            case_id=self.id,
            title=self.title,
            source_material=source_material,
            premise=self.premise,
            opponent=self.opponent,
            audience=self.audience,
            truth=self.truth,
            entities=self.seed_entities,
            candidate_viewpoints=self.selectable_roles(),
            opening_event=replace(self.opening_event),
            research_notes=research_notes,
        )

    def to_frozen_world(
        self,
        *,
        allowed_turn_counts: tuple[int, ...] = (4, 6, 8, 10),
        ending_bands: tuple[WorldEndingBand, ...] | None = None,
        dimension_defs: tuple[WorldDimensionDef, ...] | None = None,
        action_grammar: WorldActionGrammar | None = None,
    ) -> FrozenInitialWorld:
        resolved_bands = ending_bands or default_world_ending_bands()
        resolved_dimension_defs = dimension_defs or default_world_dimension_defs(self.initial_world.to_dimension_map())
        return FrozenInitialWorld(
            world_id=self.id,
            title=self.title,
            premise=self.premise,
            player_role=self.player_role,
            player_secret=self.player_secret,
            objective=self.objective,
            opponent=self.opponent,
            audience=self.audience,
            truth=self.truth,
            selectable_roles=self.selectable_roles(),
            allowed_turn_counts=allowed_turn_counts,
            opening_event=replace(self.opening_event),
            initial_dimensions=tuple(self.initial_world.to_dimension_map().items()),
            entities=self.seed_entities,
            ending_bands=resolved_bands,
            dimension_defs=resolved_dimension_defs,
            action_grammar=action_grammar or default_world_action_grammar(self.actions),
        )


def default_world_ending_bands() -> tuple[WorldEndingBand, ...]:
    return (
        WorldEndingBand(min_score=85, ending_id="phoenix-rebound", label="凤凰回升", description="你不但稳住了局势，还把叙事重新拉回到自己有利的位置。"),
        WorldEndingBand(min_score=65, ending_id="hard-stabilized", label="艰难稳盘", description="你付出不少代价，才勉强把局势按回可控区间。"),
        WorldEndingBand(min_score=45, ending_id="fragile-truce", label="脆弱停火", description="你暂时止血，但信任裂缝没有真正修复。"),
        WorldEndingBand(min_score=25, ending_id="pyrrhic-survival", label="惨胜续命", description="你保住了部分控制权，但代价高到几乎透支未来。"),
        WorldEndingBand(min_score=0, ending_id="collapse", label="失控崩解", description="局势脱离了你的掌控，外部叙事和内部秩序一同崩塌。"),
    )


def default_world_dimension_defs(initial_dimensions: dict[str, int]) -> tuple[WorldDimensionDef, ...]:
    defaults = {
        "credibility": ("公信力", "higher_is_better", 60, 35, 20),
        "treasury": ("资源储备", "higher_is_better", 45, 25, 10),
        "pressure": ("压力", "lower_is_better", 55, 75, 90),
        "price": ("市场价格", "higher_is_better", 50, 30, 15),
        "liquidity": ("流动性", "higher_is_better", 55, 30, 15),
        "sell_pressure": ("抛压", "lower_is_better", 45, 65, 80),
        "volatility": ("波动", "lower_is_better", 45, 65, 80),
        "community_panic": ("群体恐慌", "lower_is_better", 45, 65, 80),
        "rumor_level": ("传言水平", "lower_is_better", 40, 60, 75),
        "narrative_control": ("叙事控制", "higher_is_better", 55, 35, 20),
        "exchange_trust": ("平台信任", "higher_is_better", 60, 35, 20),
        "control": ("控制权", "higher_is_better", 60, 35, 20),
    }
    dimension_defs: list[WorldDimensionDef] = []
    for key in initial_dimensions:
        label, direction, warning, crisis, terminal = defaults.get(key, (key, "balanced", 50, 70, 85))
        dimension_defs.append(
            WorldDimensionDef(
                key=key,
                label=label,
                description=f"{label} 维度。",
                direction_of_health=direction,
                warning_threshold=warning,
                crisis_threshold=crisis,
                terminal_threshold=terminal,
            )
        )
    return tuple(dimension_defs)


def default_world_action_grammar(actions: tuple[ActionCard, ...]) -> WorldActionGrammar:
    cost_types = tuple(
        ActionCostType(key=key, label=label, description=description)
        for key, label, description in (
            ("public", "公开代价", "带来公开关注、质疑或舆论压力。"),
            ("private", "私下协调代价", "需要消耗私下协调空间或关系信用。"),
            ("finance", "资源代价", "需要消耗预算、现金或资产缓冲。"),
            ("legal", "制度代价", "需要承担程序、审计或制度约束。"),
            ("delay", "时机代价", "通过拖延换取喘息，但损失先手。"),
        )
    )
    rules = tuple(
        ActionGenerationRule(
            key=action.id,
            label=action.label,
            description=action.description,
            trigger_dimensions=tuple(dict.fromkeys((*_action_upside_axes(action), *_action_downside_axes(action)))),
            preferred_upside_dimensions=_action_upside_axes(action),
            likely_downside_dimensions=_action_downside_axes(action),
            allowed_cost_types=(action.tag,),
            minimum_upside_count=max(1, len(_action_upside_axes(action))),
            minimum_downside_count=max(1, len(_action_downside_axes(action))),
            max_upside_count=max(1, len(_action_upside_axes(action))),
            max_downside_count=max(1, len(_action_downside_axes(action))),
            intensity_range=_action_intensity_range(action),
            tags=(action.tag,),
        )
        for action in actions
    )
    return WorldActionGrammar(
        rules=rules,
        cost_types=cost_types,
        menu_size=min(4, len(actions)) if actions else 4,
    )


def infer_urgent_dimensions(dimensions: dict[str, int], dimension_defs: tuple[WorldDimensionDef, ...]) -> tuple[str, ...]:
    scored = sorted(
        ((dimension.key, _dimension_urgency_score(dimensions.get(dimension.key, 0), dimension)) for dimension in dimension_defs),
        key=lambda item: item[1],
        reverse=True,
    )
    return tuple(key for key, score in scored if score > 0)[:4]


def infer_unstable_dimensions(dimensions: dict[str, int], dimension_defs: tuple[WorldDimensionDef, ...]) -> tuple[str, ...]:
    unstable: list[str] = []
    for dimension in dimension_defs:
        value = dimensions.get(dimension.key, 0)
        if dimension.direction_of_health == "higher_is_better" and dimension.crisis_threshold is not None and value <= dimension.crisis_threshold:
            unstable.append(dimension.key)
        elif dimension.direction_of_health == "lower_is_better" and dimension.crisis_threshold is not None and value >= dimension.crisis_threshold:
            unstable.append(dimension.key)
        elif dimension.direction_of_health == "balanced" and abs(value - 50) >= 20:
            unstable.append(dimension.key)
    return tuple(unstable)


def _dimension_urgency_score(value: int, dimension: WorldDimensionDef) -> int:
    warning = dimension.warning_threshold if dimension.warning_threshold is not None else 50
    if dimension.direction_of_health == "higher_is_better":
        return max(0, warning - value)
    if dimension.direction_of_health == "lower_is_better":
        return max(0, value - warning)
    return abs(value - 50)


def _action_upside_axes(action: ActionCard) -> tuple[str, ...]:
    axes: list[str] = []
    if action.narrative_shift > 0:
        axes.append("narrative_control")
    if action.exchange_shift + action.exchange_trust_shift > 0:
        axes.append("exchange_trust")
    if action.liquidity_shift > 0:
        axes.append("liquidity")
    if action.treasury_shift > 0:
        axes.append("treasury")
    if action.control_shift > 0:
        axes.append("control")
    if action.volatility_shift < 0:
        axes.append("volatility")
    if action.kol_trust_shift > 0:
        axes.append("rumor_level")
    if action.whale_trust_shift > 0:
        axes.append("sell_pressure")
    if action.public_pressure < 0:
        axes.append("pressure")
    return tuple(dict.fromkeys(axes or ["control"]))


def _action_downside_axes(action: ActionCard) -> tuple[str, ...]:
    axes: list[str] = []
    if action.narrative_shift < 0:
        axes.append("narrative_control")
    if action.exchange_shift + action.exchange_trust_shift < 0:
        axes.append("exchange_trust")
    if action.liquidity_shift < 0:
        axes.append("liquidity")
    if action.treasury_shift < 0:
        axes.append("treasury")
    if action.control_shift < 0:
        axes.append("control")
    if action.volatility_shift > 0:
        axes.append("volatility")
    if action.kol_trust_shift < 0:
        axes.append("rumor_level")
    if action.whale_trust_shift < 0:
        axes.append("sell_pressure")
    if action.public_pressure > 0:
        axes.append("pressure")
    return tuple(dict.fromkeys(axes or ["pressure"]))


def _action_intensity_range(action: ActionCard) -> tuple[int, int]:
    impact_cost = (
        max(0, action.public_pressure)
        + max(0, -action.narrative_shift)
        + max(0, -(action.exchange_shift + action.exchange_trust_shift))
        + max(0, -action.liquidity_shift)
        + max(0, -action.treasury_shift)
        + max(0, -action.control_shift)
        + max(0, action.volatility_shift)
        + max(0, -action.kol_trust_shift)
        + max(0, -action.whale_trust_shift)
    )
    if impact_cost <= 6:
        return (1, 1)
    if impact_cost <= 14:
        return (2, 2)
    if impact_cost <= 24:
        return (3, 3)
    return (4, 4)


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
