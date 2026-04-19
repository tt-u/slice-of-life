from eventforge.domain import FrozenInitialWorld, MaterialResearchPack, ScenarioDefinition, WorldEndingBand
from eventforge.scenarios import FLASH_CRASH_SCENARIO


def test_scenario_exports_material_research_pack_with_viewpoints() -> None:
    pack = FLASH_CRASH_SCENARIO.to_material_research_pack(source_material="公开材料摘要")

    assert isinstance(pack, MaterialResearchPack)
    assert pack.case_id == FLASH_CRASH_SCENARIO.id
    assert pack.title == FLASH_CRASH_SCENARIO.title
    assert pack.source_material == "公开材料摘要"
    assert pack.candidate_viewpoints == (FLASH_CRASH_SCENARIO.player_role,)
    assert pack.entities == FLASH_CRASH_SCENARIO.seed_entities


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
