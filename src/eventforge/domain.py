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

    def to_payload(self) -> dict[str, object]:
        return {
            "turn_index": self.turn_index,
            "turns_total": self.turns_total,
            "selected_player_role": self.selected_player_role,
            "objective": self.objective,
            "dominant_tensions": list(self.dominant_tensions),
            "urgent_dimensions": list(self.urgent_dimensions),
            "unstable_dimensions": list(self.unstable_dimensions),
            "recent_action_summaries": list(self.recent_action_summaries),
        }

    @classmethod
    def from_payload(cls, payload: object) -> "TurnSituation":
        if not isinstance(payload, dict):
            raise TypeError("Turn situation payload must be a dict")
        return cls(
            turn_index=int(payload["turn_index"]),
            turns_total=int(payload["turns_total"]),
            selected_player_role=str(payload["selected_player_role"]),
            objective=str(payload["objective"]),
            dominant_tensions=tuple(str(item) for item in payload.get("dominant_tensions", [])),
            urgent_dimensions=tuple(str(item) for item in payload.get("urgent_dimensions", [])),
            unstable_dimensions=tuple(str(item) for item in payload.get("unstable_dimensions", [])),
            recent_action_summaries=tuple(str(item) for item in payload.get("recent_action_summaries", [])),
        )


@dataclass(frozen=True, slots=True)
class ActionGenerationContext:
    world_title: str
    player_role: str
    dimensions: dict[str, int]
    dimension_defs: tuple[WorldDimensionDef, ...]
    situation: TurnSituation
    action_grammar: WorldActionGrammar

    def to_payload(self) -> dict[str, object]:
        return {
            "world_title": self.world_title,
            "player_role": self.player_role,
            "dimensions": dict(self.dimensions),
            "dimension_defs": [world_dimension_def_to_payload(dimension) for dimension in self.dimension_defs],
            "situation": self.situation.to_payload(),
            "action_grammar": world_action_grammar_to_payload(self.action_grammar),
        }

    @classmethod
    def from_payload(cls, payload: object) -> "ActionGenerationContext":
        if not isinstance(payload, dict):
            raise TypeError("Action generation context payload must be a dict")
        return cls(
            world_title=str(payload["world_title"]),
            player_role=str(payload["player_role"]),
            dimensions={str(key): int(value) for key, value in dict(payload.get("dimensions", {})).items()},
            dimension_defs=tuple(world_dimension_def_from_payload(item) for item in payload.get("dimension_defs", [])),
            situation=TurnSituation.from_payload(payload["situation"]),
            action_grammar=world_action_grammar_from_payload(payload["action_grammar"]),
        )


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

    def __post_init__(self) -> None:
        if not self.upside_dimensions:
            raise ValueError("Generated actions must include at least one upside dimension")
        if not self.downside_dimensions:
            raise ValueError("Generated actions must include at least one downside dimension")
        overlap = set(self.upside_dimensions) & set(self.downside_dimensions)
        if overlap:
            raise ValueError("Generated action upside and downside dimensions must not overlap")

    def to_payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "rationale": self.rationale,
            "upside_dimensions": list(self.upside_dimensions),
            "downside_dimensions": list(self.downside_dimensions),
            "upside_magnitude": dict(self.upside_magnitude),
            "downside_magnitude": dict(self.downside_magnitude),
            "cost_types": list(self.cost_types),
            "affected_entities": list(self.affected_entities),
            "commitment_tier": self.commitment_tier,
            "tags": list(self.tags),
        }

    @classmethod
    def from_payload(cls, payload: object) -> "GeneratedAction":
        if not isinstance(payload, dict):
            raise TypeError("Generated action payload must be a dict")
        return cls(
            id=str(payload["id"]),
            label=str(payload["label"]),
            description=str(payload["description"]),
            rationale=str(payload["rationale"]),
            upside_dimensions=tuple(str(item) for item in payload.get("upside_dimensions", [])),
            downside_dimensions=tuple(str(item) for item in payload.get("downside_dimensions", [])),
            upside_magnitude={str(key): int(value) for key, value in dict(payload.get("upside_magnitude", {})).items()},
            downside_magnitude={str(key): int(value) for key, value in dict(payload.get("downside_magnitude", {})).items()},
            cost_types=tuple(str(item) for item in payload.get("cost_types", [])),
            affected_entities=tuple(str(item) for item in payload.get("affected_entities", [])),
            commitment_tier=str(payload["commitment_tier"]),
            tags=tuple(str(item) for item in payload.get("tags", [])),
        )


@dataclass(frozen=True, slots=True)
class AgentStateAxisDef:
    key: str
    label: str
    description: str
    min_value: int = 0
    max_value: int = 100
    max_delta_per_turn: int = 20

    def to_payload(self) -> dict[str, object]:
        return {
            "key": self.key,
            "label": self.label,
            "description": self.description,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "max_delta_per_turn": self.max_delta_per_turn,
        }

    @classmethod
    def from_payload(cls, payload: object) -> "AgentStateAxisDef":
        if not isinstance(payload, dict):
            raise TypeError("Agent state axis payload must be a dict")
        return cls(
            key=str(payload["key"]),
            label=str(payload["label"]),
            description=str(payload["description"]),
            min_value=int(payload.get("min_value", 0)),
            max_value=int(payload.get("max_value", 100)),
            max_delta_per_turn=int(payload.get("max_delta_per_turn", 20)),
        )


@dataclass(frozen=True, slots=True)
class AgentRelationshipState:
    target_entity_id: str
    alignment: int
    strain: int
    dependency: int
    visibility: int = 50

    def to_payload(self) -> dict[str, object]:
        return {
            "target_entity_id": self.target_entity_id,
            "alignment": self.alignment,
            "strain": self.strain,
            "dependency": self.dependency,
            "visibility": self.visibility,
        }

    @classmethod
    def from_payload(cls, payload: object) -> "AgentRelationshipState":
        if not isinstance(payload, dict):
            raise TypeError("Agent relationship payload must be a dict")
        return cls(
            target_entity_id=str(payload["target_entity_id"]),
            alignment=int(payload["alignment"]),
            strain=int(payload["strain"]),
            dependency=int(payload["dependency"]),
            visibility=int(payload.get("visibility", 50)),
        )


@dataclass(frozen=True, slots=True)
class AgentMemoryEntry:
    turn_index: int
    action_id: str
    summary: str
    salience: int
    valence: int

    def to_payload(self) -> dict[str, object]:
        return {
            "turn_index": self.turn_index,
            "action_id": self.action_id,
            "summary": self.summary,
            "salience": self.salience,
            "valence": self.valence,
        }

    @classmethod
    def from_payload(cls, payload: object) -> "AgentMemoryEntry":
        if not isinstance(payload, dict):
            raise TypeError("Agent memory payload must be a dict")
        return cls(
            turn_index=int(payload["turn_index"]),
            action_id=str(payload["action_id"]),
            summary=str(payload["summary"]),
            salience=int(payload["salience"]),
            valence=int(payload["valence"]),
        )


@dataclass(frozen=True, slots=True)
class AgentRunState:
    agent_id: str
    agent_name: str
    role: str
    stance: str
    current_objective: str
    scalar_state: dict[str, int]
    relationships: tuple[AgentRelationshipState, ...] = ()
    memories: tuple[AgentMemoryEntry, ...] = ()
    triggered_hooks: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, object]:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "role": self.role,
            "stance": self.stance,
            "current_objective": self.current_objective,
            "scalar_state": dict(self.scalar_state),
            "relationships": [relationship.to_payload() for relationship in self.relationships],
            "memories": [memory.to_payload() for memory in self.memories],
            "triggered_hooks": list(self.triggered_hooks),
        }

    @classmethod
    def from_payload(cls, payload: object) -> "AgentRunState":
        if not isinstance(payload, dict):
            raise TypeError("Agent run-state payload must be a dict")
        return cls(
            agent_id=str(payload["agent_id"]),
            agent_name=str(payload["agent_name"]),
            role=str(payload["role"]),
            stance=str(payload["stance"]),
            current_objective=str(payload["current_objective"]),
            scalar_state={str(key): int(value) for key, value in dict(payload.get("scalar_state", {})).items()},
            relationships=tuple(AgentRelationshipState.from_payload(item) for item in payload.get("relationships", [])),
            memories=tuple(AgentMemoryEntry.from_payload(item) for item in payload.get("memories", [])),
            triggered_hooks=tuple(str(item) for item in payload.get("triggered_hooks", [])),
        )


@dataclass(frozen=True, slots=True)
class AgentReactionBoundaries:
    scalar_axes: tuple[AgentStateAxisDef, ...]
    max_relationship_delta_per_turn: int = 18
    max_dimension_impacts_per_reaction: int = 2
    max_dimension_delta_per_reaction: int = 12
    max_relationship_updates_per_reaction: int = 2
    max_hooks_per_reaction: int = 1
    memory_limit: int = 3
    allowed_hook_tags: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, object]:
        return {
            "scalar_axes": [axis.to_payload() for axis in self.scalar_axes],
            "max_relationship_delta_per_turn": self.max_relationship_delta_per_turn,
            "max_dimension_impacts_per_reaction": self.max_dimension_impacts_per_reaction,
            "max_dimension_delta_per_reaction": self.max_dimension_delta_per_reaction,
            "max_relationship_updates_per_reaction": self.max_relationship_updates_per_reaction,
            "max_hooks_per_reaction": self.max_hooks_per_reaction,
            "memory_limit": self.memory_limit,
            "allowed_hook_tags": list(self.allowed_hook_tags),
        }

    @classmethod
    def from_payload(cls, payload: object) -> "AgentReactionBoundaries":
        if not isinstance(payload, dict):
            raise TypeError("Agent reaction boundaries payload must be a dict")
        return cls(
            scalar_axes=tuple(AgentStateAxisDef.from_payload(item) for item in payload.get("scalar_axes", [])),
            max_relationship_delta_per_turn=int(payload.get("max_relationship_delta_per_turn", 18)),
            max_dimension_impacts_per_reaction=int(payload.get("max_dimension_impacts_per_reaction", 2)),
            max_dimension_delta_per_reaction=int(payload.get("max_dimension_delta_per_reaction", 12)),
            max_relationship_updates_per_reaction=int(payload.get("max_relationship_updates_per_reaction", 2)),
            max_hooks_per_reaction=int(payload.get("max_hooks_per_reaction", 1)),
            memory_limit=int(payload.get("memory_limit", 3)),
            allowed_hook_tags=tuple(str(item) for item in payload.get("allowed_hook_tags", [])),
        )


@dataclass(frozen=True, slots=True)
class AgentReactionContext:
    world_id: str
    world_title: str
    turn_index: int
    turns_total: int
    player_role: str
    player_objective: str
    chosen_action_id: str
    chosen_action_label: str
    chosen_action_summary: str
    current_dimensions: dict[str, int]
    urgent_dimensions: tuple[str, ...]
    unstable_dimensions: tuple[str, ...]
    dominant_tensions: tuple[str, ...]
    acting_agent: AgentRunState
    relevant_entities: tuple[str, ...]
    recent_turn_summaries: tuple[str, ...]
    boundaries: AgentReactionBoundaries


@dataclass(frozen=True, slots=True)
class AgentReactionProposal:
    summary: str
    stance: str
    updated_objective: str
    scalar_deltas: dict[str, int]
    relationship_deltas: dict[str, dict[str, int]]
    dimension_impacts: dict[str, int]
    follow_on_hooks: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, object]:
        return {
            "summary": self.summary,
            "stance": self.stance,
            "updated_objective": self.updated_objective,
            "scalar_deltas": dict(self.scalar_deltas),
            "relationship_deltas": {str(key): dict(value) for key, value in self.relationship_deltas.items()},
            "dimension_impacts": dict(self.dimension_impacts),
            "follow_on_hooks": list(self.follow_on_hooks),
        }

    @classmethod
    def from_payload(cls, payload: object) -> "AgentReactionProposal":
        if not isinstance(payload, dict):
            raise TypeError("Agent reaction proposal payload must be a dict")
        return cls(
            summary=str(payload["summary"]),
            stance=str(payload["stance"]),
            updated_objective=str(payload["updated_objective"]),
            scalar_deltas={str(key): int(value) for key, value in dict(payload.get("scalar_deltas", {})).items()},
            relationship_deltas={
                str(target): {str(field_name): int(delta) for field_name, delta in dict(fields).items()}
                for target, fields in dict(payload.get("relationship_deltas", {})).items()
            },
            dimension_impacts={str(key): int(value) for key, value in dict(payload.get("dimension_impacts", {})).items()},
            follow_on_hooks=tuple(str(item) for item in payload.get("follow_on_hooks", [])),
        )


@dataclass(frozen=True, slots=True)
class AgentReactionResult:
    agent_id: str
    agent_name: str
    role: str
    summary: str
    stance: str
    objective: str
    applied_scalar_deltas: dict[str, int]
    applied_relationship_deltas: dict[str, dict[str, int]]
    applied_dimension_impacts: dict[str, int]
    triggered_hooks: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WorldEndingBand:
    min_score: int
    ending_id: str
    label: str
    description: str


@dataclass(frozen=True, slots=True)
class EvidenceNote:
    source_title: str
    source_url: str
    note: str

    def to_payload(self) -> dict[str, object]:
        return {
            "source_title": self.source_title,
            "source_url": self.source_url,
            "note": self.note,
        }

    @classmethod
    def from_payload(cls, payload: object) -> "EvidenceNote":
        if not isinstance(payload, dict):
            raise TypeError("Evidence note payload must be a dict")
        return cls(
            source_title=str(payload["source_title"]),
            source_url=str(payload["source_url"]),
            note=str(payload["note"]),
        )


@dataclass(frozen=True, slots=True)
class ResearchRelationship:
    target_entity_id: str
    relation_type: str
    summary: str

    def to_payload(self) -> dict[str, object]:
        return {
            "target_entity_id": self.target_entity_id,
            "relation_type": self.relation_type,
            "summary": self.summary,
        }

    @classmethod
    def from_payload(cls, payload: object) -> "ResearchRelationship":
        if not isinstance(payload, dict):
            raise TypeError("Research relationship payload must be a dict")
        return cls(
            target_entity_id=str(payload["target_entity_id"]),
            relation_type=str(payload["relation_type"]),
            summary=str(payload["summary"]),
        )


@dataclass(frozen=True, slots=True)
class ResearchDispute:
    key: str
    claim: str
    sides: tuple[str, ...]
    status: str

    def to_payload(self) -> dict[str, object]:
        return {
            "key": self.key,
            "claim": self.claim,
            "sides": list(self.sides),
            "status": self.status,
        }

    @classmethod
    def from_payload(cls, payload: object) -> "ResearchDispute":
        if not isinstance(payload, dict):
            raise TypeError("Research dispute payload must be a dict")
        return cls(
            key=str(payload["key"]),
            claim=str(payload["claim"]),
            sides=tuple(str(item) for item in payload.get("sides", [])),
            status=str(payload["status"]),
        )


@dataclass(frozen=True, slots=True)
class EntityResearchCard:
    entity_id: str
    name: str
    role: str
    stance: str
    public_position: str
    conflict_stakes: str
    notable_pressures: tuple[str, ...] = ()
    relationships: tuple[ResearchRelationship, ...] = ()
    evidence: tuple[EvidenceNote, ...] = ()

    def to_payload(self) -> dict[str, object]:
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "role": self.role,
            "stance": self.stance,
            "public_position": self.public_position,
            "conflict_stakes": self.conflict_stakes,
            "notable_pressures": list(self.notable_pressures),
            "relationships": [relationship.to_payload() for relationship in self.relationships],
            "evidence": [note.to_payload() for note in self.evidence],
        }

    @classmethod
    def from_payload(cls, payload: object) -> "EntityResearchCard":
        if not isinstance(payload, dict):
            raise TypeError("Entity research card payload must be a dict")
        return cls(
            entity_id=str(payload["entity_id"]),
            name=str(payload["name"]),
            role=str(payload["role"]),
            stance=str(payload["stance"]),
            public_position=str(payload["public_position"]),
            conflict_stakes=str(payload["conflict_stakes"]),
            notable_pressures=tuple(str(item) for item in payload.get("notable_pressures", [])),
            relationships=tuple(ResearchRelationship.from_payload(item) for item in payload.get("relationships", [])),
            evidence=tuple(EvidenceNote.from_payload(item) for item in payload.get("evidence", [])),
        )


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
    entity_cards: tuple[EntityResearchCard, ...] = ()
    disputed_points: tuple[ResearchDispute, ...] = ()

    def to_payload(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "title": self.title,
            "source_material": self.source_material,
            "premise": self.premise,
            "opponent": self.opponent,
            "audience": list(self.audience),
            "truth": self.truth,
            "entities": [seed_entity_to_payload(entity) for entity in self.entities],
            "candidate_viewpoints": list(self.candidate_viewpoints),
            "opening_event": world_event_to_payload(self.opening_event),
            "research_notes": list(self.research_notes),
            "entity_cards": [card.to_payload() for card in self.entity_cards],
            "disputed_points": [dispute.to_payload() for dispute in self.disputed_points],
        }

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "MaterialResearchPack":
        return cls(
            case_id=str(payload["case_id"]),
            title=str(payload["title"]),
            source_material=str(payload["source_material"]),
            premise=str(payload["premise"]),
            opponent=str(payload["opponent"]),
            audience=tuple(str(item) for item in payload.get("audience", [])),
            truth=str(payload["truth"]),
            entities=tuple(seed_entity_from_payload(item) for item in payload.get("entities", [])),
            candidate_viewpoints=tuple(str(item) for item in payload.get("candidate_viewpoints", [])),
            opening_event=world_event_from_payload(payload["opening_event"]),
            research_notes=tuple(str(item) for item in payload.get("research_notes", [])),
            entity_cards=tuple(EntityResearchCard.from_payload(item) for item in payload.get("entity_cards", [])),
            disputed_points=tuple(ResearchDispute.from_payload(item) for item in payload.get("disputed_points", [])),
        )


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
    reaction_boundaries: AgentReactionBoundaries | None = None

    def to_payload(self) -> dict[str, object]:
        return {
            "world_id": self.world_id,
            "title": self.title,
            "premise": self.premise,
            "player_role": self.player_role,
            "player_secret": self.player_secret,
            "objective": self.objective,
            "opponent": self.opponent,
            "audience": list(self.audience),
            "truth": self.truth,
            "selectable_roles": list(self.selectable_roles),
            "allowed_turn_counts": list(self.allowed_turn_counts),
            "opening_event": world_event_to_payload(self.opening_event),
            "initial_dimensions": [[key, value] for key, value in self.initial_dimensions],
            "entities": [seed_entity_to_payload(entity) for entity in self.entities],
            "ending_bands": [world_ending_band_to_payload(band) for band in self.ending_bands],
            "dimension_defs": [world_dimension_def_to_payload(dimension) for dimension in self.dimension_defs],
            "action_grammar": world_action_grammar_to_payload(self.action_grammar) if self.action_grammar is not None else None,
            "reaction_boundaries": self.reaction_boundaries.to_payload() if self.reaction_boundaries is not None else None,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "FrozenInitialWorld":
        return cls(
            world_id=str(payload["world_id"]),
            title=str(payload["title"]),
            premise=str(payload["premise"]),
            player_role=str(payload["player_role"]),
            player_secret=str(payload["player_secret"]),
            objective=str(payload["objective"]),
            opponent=str(payload["opponent"]),
            audience=tuple(str(item) for item in payload.get("audience", [])),
            truth=str(payload["truth"]),
            selectable_roles=tuple(str(item) for item in payload.get("selectable_roles", [])),
            allowed_turn_counts=tuple(int(item) for item in payload.get("allowed_turn_counts", [])),
            opening_event=world_event_from_payload(payload["opening_event"]),
            initial_dimensions=tuple((str(key), int(value)) for key, value in payload.get("initial_dimensions", [])),
            entities=tuple(seed_entity_from_payload(item) for item in payload.get("entities", [])),
            ending_bands=tuple(world_ending_band_from_payload(item) for item in payload.get("ending_bands", [])),
            dimension_defs=tuple(world_dimension_def_from_payload(item) for item in payload.get("dimension_defs", [])),
            action_grammar=world_action_grammar_from_payload(payload["action_grammar"]) if payload.get("action_grammar") is not None else None,
            reaction_boundaries=AgentReactionBoundaries.from_payload(payload["reaction_boundaries"]) if payload.get("reaction_boundaries") is not None else None,
        )

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
    action: GeneratedAction
    reason: str


@dataclass(frozen=True, slots=True)
class WorldEvent:
    headline: str
    summary: str
    severity: int
    actor_id: str = "system"
    actor_name: str = "System"
    state_delta: dict[str, int] = field(default_factory=dict)


def seed_entity_to_payload(entity: SeedEntity) -> dict[str, object]:
    return {
        "id": entity.id,
        "name": entity.name,
        "role": entity.role,
        "public_goal": entity.public_goal,
        "pressure_point": entity.pressure_point,
        "starting_trust": entity.starting_trust,
        "influence": entity.influence,
        "stance": entity.stance,
        "details": entity.details,
    }


def seed_entity_from_payload(payload: object) -> SeedEntity:
    if not isinstance(payload, dict):
        raise TypeError("Seed entity payload must be a dict")
    return SeedEntity(
        id=str(payload["id"]),
        name=str(payload["name"]),
        role=str(payload["role"]),
        public_goal=str(payload["public_goal"]),
        pressure_point=str(payload["pressure_point"]),
        starting_trust=int(payload["starting_trust"]),
        influence=int(payload["influence"]),
        stance=str(payload["stance"]),
        details=str(payload["details"]),
    )


def world_event_to_payload(event: WorldEvent) -> dict[str, object]:
    return {
        "headline": event.headline,
        "summary": event.summary,
        "severity": event.severity,
        "actor_id": event.actor_id,
        "actor_name": event.actor_name,
        "state_delta": dict(event.state_delta),
    }


def world_event_from_payload(payload: object) -> WorldEvent:
    if not isinstance(payload, dict):
        raise TypeError("World event payload must be a dict")
    return WorldEvent(
        headline=str(payload["headline"]),
        summary=str(payload["summary"]),
        severity=int(payload["severity"]),
        actor_id=str(payload.get("actor_id", "system")),
        actor_name=str(payload.get("actor_name", "System")),
        state_delta={str(key): int(value) for key, value in dict(payload.get("state_delta", {})).items()},
    )


def world_dimension_def_to_payload(dimension: WorldDimensionDef) -> dict[str, object]:
    return {
        "key": dimension.key,
        "label": dimension.label,
        "description": dimension.description,
        "direction_of_health": dimension.direction_of_health,
        "warning_threshold": dimension.warning_threshold,
        "crisis_threshold": dimension.crisis_threshold,
        "terminal_threshold": dimension.terminal_threshold,
    }


def world_dimension_def_from_payload(payload: object) -> WorldDimensionDef:
    if not isinstance(payload, dict):
        raise TypeError("World dimension payload must be a dict")
    return WorldDimensionDef(
        key=str(payload["key"]),
        label=str(payload["label"]),
        description=str(payload["description"]),
        direction_of_health=str(payload["direction_of_health"]),
        warning_threshold=int(payload["warning_threshold"]) if payload.get("warning_threshold") is not None else None,
        crisis_threshold=int(payload["crisis_threshold"]) if payload.get("crisis_threshold") is not None else None,
        terminal_threshold=int(payload["terminal_threshold"]) if payload.get("terminal_threshold") is not None else None,
    )


def action_cost_type_to_payload(cost_type: ActionCostType) -> dict[str, object]:
    return {
        "key": cost_type.key,
        "label": cost_type.label,
        "description": cost_type.description,
    }


def action_cost_type_from_payload(payload: object) -> ActionCostType:
    if not isinstance(payload, dict):
        raise TypeError("Action cost type payload must be a dict")
    return ActionCostType(
        key=str(payload["key"]),
        label=str(payload["label"]),
        description=str(payload["description"]),
    )


def action_generation_rule_to_payload(rule: ActionGenerationRule) -> dict[str, object]:
    return {
        "key": rule.key,
        "label": rule.label,
        "description": rule.description,
        "trigger_dimensions": list(rule.trigger_dimensions),
        "preferred_upside_dimensions": list(rule.preferred_upside_dimensions),
        "likely_downside_dimensions": list(rule.likely_downside_dimensions),
        "allowed_cost_types": list(rule.allowed_cost_types),
        "minimum_upside_count": rule.minimum_upside_count,
        "minimum_downside_count": rule.minimum_downside_count,
        "max_upside_count": rule.max_upside_count,
        "max_downside_count": rule.max_downside_count,
        "intensity_range": list(rule.intensity_range),
        "tags": list(rule.tags),
    }


def action_generation_rule_from_payload(payload: object) -> ActionGenerationRule:
    if not isinstance(payload, dict):
        raise TypeError("Action generation rule payload must be a dict")
    return ActionGenerationRule(
        key=str(payload["key"]),
        label=str(payload["label"]),
        description=str(payload["description"]),
        trigger_dimensions=tuple(str(item) for item in payload.get("trigger_dimensions", [])),
        preferred_upside_dimensions=tuple(str(item) for item in payload.get("preferred_upside_dimensions", [])),
        likely_downside_dimensions=tuple(str(item) for item in payload.get("likely_downside_dimensions", [])),
        allowed_cost_types=tuple(str(item) for item in payload.get("allowed_cost_types", [])),
        minimum_upside_count=int(payload.get("minimum_upside_count", 1)),
        minimum_downside_count=int(payload.get("minimum_downside_count", 1)),
        max_upside_count=int(payload.get("max_upside_count", 2)),
        max_downside_count=int(payload.get("max_downside_count", 2)),
        intensity_range=tuple(int(item) for item in payload.get("intensity_range", (1, 3))),
        tags=tuple(str(item) for item in payload.get("tags", [])),
    )


def world_action_grammar_to_payload(grammar: WorldActionGrammar) -> dict[str, object]:
    return {
        "rules": [action_generation_rule_to_payload(rule) for rule in grammar.rules],
        "cost_types": [action_cost_type_to_payload(cost_type) for cost_type in grammar.cost_types],
        "forbidden_pairs": [[left, right] for left, right in grammar.forbidden_pairs],
        "forbidden_tags": list(grammar.forbidden_tags),
        "required_tradeoff": grammar.required_tradeoff,
        "menu_size": grammar.menu_size,
        "low_commitment_slots": grammar.low_commitment_slots,
        "medium_commitment_slots": grammar.medium_commitment_slots,
        "high_commitment_slots": grammar.high_commitment_slots,
    }


def world_action_grammar_from_payload(payload: object) -> WorldActionGrammar:
    if not isinstance(payload, dict):
        raise TypeError("World action grammar payload must be a dict")
    return WorldActionGrammar(
        rules=tuple(action_generation_rule_from_payload(item) for item in payload.get("rules", [])),
        cost_types=tuple(action_cost_type_from_payload(item) for item in payload.get("cost_types", [])),
        forbidden_pairs=tuple((str(left), str(right)) for left, right in payload.get("forbidden_pairs", [])),
        forbidden_tags=tuple(str(item) for item in payload.get("forbidden_tags", [])),
        required_tradeoff=bool(payload.get("required_tradeoff", True)),
        menu_size=int(payload.get("menu_size", 4)),
        low_commitment_slots=int(payload.get("low_commitment_slots", 1)),
        medium_commitment_slots=int(payload.get("medium_commitment_slots", 2)),
        high_commitment_slots=int(payload.get("high_commitment_slots", 1)),
    )


def world_ending_band_to_payload(band: WorldEndingBand) -> dict[str, object]:
    return {
        "min_score": band.min_score,
        "ending_id": band.ending_id,
        "label": band.label,
        "description": band.description,
    }


def world_ending_band_from_payload(payload: object) -> WorldEndingBand:
    if not isinstance(payload, dict):
        raise TypeError("World ending band payload must be a dict")
    return WorldEndingBand(
        min_score=int(payload["min_score"]),
        ending_id=str(payload["ending_id"]),
        label=str(payload["label"]),
        description=str(payload["description"]),
    )


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
    action_grammar: WorldActionGrammar | None = None

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
        reaction_boundaries: AgentReactionBoundaries | None = None,
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
            action_grammar=action_grammar or self.action_grammar or default_world_action_grammar(self.actions),
            reaction_boundaries=reaction_boundaries or default_agent_reaction_boundaries(),
        )


def default_agent_reaction_boundaries() -> AgentReactionBoundaries:
    return AgentReactionBoundaries(
        scalar_axes=(
            AgentStateAxisDef(
                key="trust_in_player",
                label="对玩家信任",
                description="是否愿意继续给玩家解释空间。",
                max_delta_per_turn=18,
            ),
            AgentStateAxisDef(
                key="pressure_load",
                label="压力负载",
                description="该代理当前承受的内外压力。",
                max_delta_per_turn=18,
            ),
            AgentStateAxisDef(
                key="escalation_drive",
                label="升级冲动",
                description="该代理是否准备把冲突推向更激烈阶段。",
                max_delta_per_turn=18,
            ),
            AgentStateAxisDef(
                key="public_alignment",
                label="公开站位",
                description="该代理是否愿意公开贴近玩家叙事。",
                max_delta_per_turn=18,
            ),
        ),
        allowed_hook_tags=("institutional_freeze", "counterattack_preparing", "public_break", "public-procedure-scrutiny"),
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
    cost_types = _default_action_cost_types()
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


def dimension_driven_world_action_grammar(
    initial_dimensions: dict[str, int],
    dimension_defs: tuple[WorldDimensionDef, ...],
    *,
    player_role: str,
    objective: str,
) -> WorldActionGrammar:
    resolved_dimension_defs = dimension_defs or default_world_dimension_defs(initial_dimensions)
    dimension_by_key = {dimension.key: dimension for dimension in resolved_dimension_defs}
    prioritized_keys = list(infer_urgent_dimensions(initial_dimensions, resolved_dimension_defs))
    for fallback_key in ("control", "credibility", "pressure", "narrative_control", *initial_dimensions.keys()):
        if fallback_key in initial_dimensions and fallback_key not in prioritized_keys:
            prioritized_keys.append(fallback_key)

    selected_keys = prioritized_keys[:4]
    rules: list[ActionGenerationRule] = []
    objective_snippet = objective[:18] if objective else "稳住局势"
    for index, dimension_key in enumerate(selected_keys, start=1):
        dimension = dimension_by_key.get(dimension_key)
        if dimension is None:
            continue
        downside_dimensions = _dimension_focus_downside_dimensions(dimension_key, initial_dimensions)
        rules.append(
            ActionGenerationRule(
                key=f"{dimension_key}-focus-{index}",
                label=f"{_dimension_focus_label_prefix(dimension)}{dimension.label}",
                description=f"以{player_role}视角优先处理{dimension.label}，推进“{objective_snippet}”，但会挤占其他操作空间。",
                trigger_dimensions=tuple(dict.fromkeys((dimension_key, *downside_dimensions))),
                preferred_upside_dimensions=(dimension_key,),
                likely_downside_dimensions=downside_dimensions,
                allowed_cost_types=_dimension_focus_cost_types(dimension_key),
                minimum_upside_count=1,
                minimum_downside_count=max(1, len(downside_dimensions)),
                max_upside_count=1,
                max_downside_count=max(1, len(downside_dimensions)),
                intensity_range=(1, 3),
                tags=("world-generated", dimension_key),
            )
        )
    return WorldActionGrammar(
        rules=tuple(rules),
        cost_types=_default_action_cost_types(),
        menu_size=min(4, len(rules)) if rules else 4,
    )


def _default_action_cost_types() -> tuple[ActionCostType, ...]:
    return tuple(
        ActionCostType(key=key, label=label, description=description)
        for key, label, description in (
            ("public", "公开代价", "带来公开关注、质疑或舆论压力。"),
            ("private", "私下协调代价", "需要消耗私下协调空间或关系信用。"),
            ("finance", "资源代价", "需要消耗预算、现金或资产缓冲。"),
            ("legal", "制度代价", "需要承担程序、审计或制度约束。"),
            ("delay", "时机代价", "通过拖延换取喘息，但损失先手。"),
        )
    )


def _dimension_focus_label_prefix(dimension: WorldDimensionDef) -> str:
    if dimension.direction_of_health == "lower_is_better":
        return "压低"
    if dimension.direction_of_health == "higher_is_better":
        return "补强"
    return "调节"


def _dimension_focus_downside_dimensions(dimension_key: str, initial_dimensions: dict[str, int]) -> tuple[str, ...]:
    fallback_map = {
        "credibility": ("pressure", "control"),
        "pressure": ("credibility", "control"),
        "narrative_control": ("credibility", "pressure"),
        "control": ("credibility", "pressure"),
        "treasury": ("pressure", "credibility"),
        "liquidity": ("treasury", "control"),
        "price": ("liquidity", "credibility"),
        "exchange_trust": ("control", "pressure"),
        "community_panic": ("credibility", "control"),
        "rumor_level": ("credibility", "control"),
        "sell_pressure": ("treasury", "credibility"),
        "volatility": ("control", "treasury"),
    }
    resolved = tuple(
        key for key in fallback_map.get(dimension_key, ("pressure", "control")) if key in initial_dimensions and key != dimension_key
    )
    if resolved:
        return resolved[:2]
    fallback = tuple(key for key in initial_dimensions if key != dimension_key)
    return fallback[:1] or (dimension_key,)


def _dimension_focus_cost_types(dimension_key: str) -> tuple[str, ...]:
    if dimension_key in {"credibility", "narrative_control", "community_panic", "rumor_level"}:
        return ("public", "delay")
    if dimension_key in {"control"}:
        return ("private", "legal")
    if dimension_key in {"treasury", "liquidity", "price", "sell_pressure", "volatility", "exchange_trust"}:
        return ("finance", "private")
    return ("private", "public")


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
