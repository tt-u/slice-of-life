from eventforge.domain import (
    FrozenInitialWorld,
    MaterialResearchPack,
    ScenarioDefinition,
    TurnSituation,
    WorldEndingBand,
)
from eventforge.scenarios import FLASH_CRASH_SCENARIO


def test_scenario_exports_material_research_pack_with_viewpoints() -> None:
    pack = FLASH_CRASH_SCENARIO.to_material_research_pack(source_material="公开材料摘要")

    assert isinstance(pack, MaterialResearchPack)
    assert pack.case_id == FLASH_CRASH_SCENARIO.id
    assert pack.title == FLASH_CRASH_SCENARIO.title
    assert pack.source_material == "公开材料摘要"
    assert pack.candidate_viewpoints == (FLASH_CRASH_SCENARIO.player_role,)
    assert pack.entities == FLASH_CRASH_SCENARIO.seed_entities


def test_material_research_pack_round_trips_through_serialized_payload() -> None:
    pack = FLASH_CRASH_SCENARIO.to_material_research_pack(
        source_material="公开材料摘要",
        research_notes=("实体来自公开报道", "保留候选对立视角"),
    )

    payload = pack.to_payload()

    assert payload["case_id"] == FLASH_CRASH_SCENARIO.id
    assert payload["source_material"] == "公开材料摘要"
    assert payload["candidate_viewpoints"] == [FLASH_CRASH_SCENARIO.player_role]
    assert payload["entities"][0]["id"] == FLASH_CRASH_SCENARIO.seed_entities[0].id
    assert payload["opening_event"]["headline"] == FLASH_CRASH_SCENARIO.opening_event.headline

    restored = MaterialResearchPack.from_payload(payload)

    assert restored == pack
    assert restored.entities[0].name == FLASH_CRASH_SCENARIO.seed_entities[0].name
    assert restored.opening_event.summary == FLASH_CRASH_SCENARIO.opening_event.summary
    assert restored.research_notes == ("实体来自公开报道", "保留候选对立视角")


def test_scenario_freezes_initial_world_into_immutable_artifact() -> None:
    frozen = FLASH_CRASH_SCENARIO.to_frozen_world()

    assert isinstance(frozen, FrozenInitialWorld)
    assert frozen.world_id == FLASH_CRASH_SCENARIO.id
    assert frozen.selectable_roles == (FLASH_CRASH_SCENARIO.player_role,)
    assert frozen.allowed_turn_counts == (4, 6, 8, 10)

    runtime_state = frozen.instantiate_state(turns_total=8)
    runtime_state.control = 1

    assert runtime_state.turns_total == 8
    assert frozen.initial_dimension_map()["control"] == FLASH_CRASH_SCENARIO.initial_world.control


def test_scenario_uses_explicit_playable_roles_when_freezing_world() -> None:
    scenario = ScenarioDefinition(
        id="campus-case",
        title="校园风波",
        premise="双方围绕处理程序持续冲突。",
        player_role="校方",
        player_secret="内部流程存在争议。",
        objective="稳住公信力。",
        opponent="另一核心阵营",
        audience=("学生", "公众"),
        truth="不同参与方都在争夺定义权。",
        opening_event=FLASH_CRASH_SCENARIO.opening_event,
        seed_entities=FLASH_CRASH_SCENARIO.seed_entities,
        actions=FLASH_CRASH_SCENARIO.actions,
        initial_world=FLASH_CRASH_SCENARIO.initial_world,
        playable_roles=("校方", "杨景媛"),
    )

    frozen = scenario.to_frozen_world(allowed_turn_counts=(5, 7))
    pack = scenario.to_material_research_pack(source_material="校园材料")

    assert frozen.selectable_roles == ("校方", "杨景媛")
    assert frozen.allowed_turn_counts == (5, 7)
    assert pack.candidate_viewpoints == ("校方", "杨景媛")


def test_frozen_world_resolves_world_local_ending_bands_deterministically() -> None:
    frozen = FLASH_CRASH_SCENARIO.to_frozen_world(
        ending_bands=(
            WorldEndingBand(min_score=80, ending_id="order-restored", label="秩序重建", description="局势基本回稳。"),
            WorldEndingBand(min_score=50, ending_id="costly-standoff", label="僵持求存", description="付出高代价后勉强维持。"),
            WorldEndingBand(min_score=0, ending_id="public-collapse", label="众矢之的", description="局势全面失控。"),
        )
    )

    assert frozen.resolve_ending_band(85).label == "秩序重建"
    assert frozen.resolve_ending_band(50).ending_id == "costly-standoff"
    assert frozen.resolve_ending_band(10).label == "众矢之的"


def test_scenario_freezes_default_world_action_grammar_from_actions() -> None:
    frozen = FLASH_CRASH_SCENARIO.to_frozen_world()

    assert frozen.action_grammar is not None
    assert frozen.action_grammar.menu_size == 4
    assert {rule.key for rule in frozen.action_grammar.rules} >= {"statement", "ama", "buyback", "freeze_wallet"}
    buyback_rule = next(rule for rule in frozen.action_grammar.rules if rule.key == "buyback")
    assert "liquidity" in buyback_rule.preferred_upside_dimensions
    assert "treasury" in buyback_rule.likely_downside_dimensions
    assert buyback_rule.minimum_upside_count >= 1
    assert buyback_rule.minimum_downside_count >= 1


def test_frozen_world_builds_action_generation_context_from_runtime_state() -> None:
    frozen = FLASH_CRASH_SCENARIO.to_frozen_world()
    state = frozen.instantiate_state(turns_total=8)
    state.community_panic = 86
    state.exchange_trust = 18
    state.liquidity = 24

    context = frozen.build_action_generation_context(
        state=state,
        situation=TurnSituation(
            turn_index=2,
            turns_total=8,
            selected_player_role="项目创始人",
            objective="稳住局面",
            dominant_tensions=("社区质疑", "平台风控"),
            urgent_dimensions=(),
            unstable_dimensions=(),
            recent_action_summaries=("上一回合先稳住社区",),
        ),
    )

    assert context.world_title == FLASH_CRASH_SCENARIO.title
    assert context.player_role == "项目创始人"
    assert context.dimensions["exchange_trust"] == 18
    assert context.action_grammar == frozen.action_grammar
    assert context.situation.urgent_dimensions[:3] == ("exchange_trust", "community_panic", "liquidity")
    assert "exchange_trust" in context.situation.unstable_dimensions


def test_frozen_world_round_trips_through_serialized_payload() -> None:
    frozen = FLASH_CRASH_SCENARIO.to_frozen_world(
        allowed_turn_counts=(5, 7),
        ending_bands=(
            WorldEndingBand(min_score=70, ending_id="hold-line", label="守住底线", description="核心秩序尚存。"),
            WorldEndingBand(min_score=0, ending_id="spiral", label="失序坠落", description="局势进入连锁下坠。"),
        ),
    )

    payload = frozen.to_payload()

    assert payload["world_id"] == FLASH_CRASH_SCENARIO.id
    assert payload["selectable_roles"] == list(frozen.selectable_roles)
    assert payload["allowed_turn_counts"] == [5, 7]
    assert payload["initial_dimensions"][0] == ["credibility", frozen.initial_dimension_map()["credibility"]]
    assert payload["dimension_defs"][0]["key"] == frozen.dimension_defs[0].key
    assert payload["action_grammar"]["rules"][0]["key"] == frozen.action_grammar.rules[0].key
    assert payload["ending_bands"][0]["label"] == "守住底线"

    restored = FrozenInitialWorld.from_payload(payload)

    assert restored == frozen
    assert restored.resolve_ending_band(85).label == "守住底线"
