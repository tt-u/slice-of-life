from dataclasses import replace

import eventforge.engine as engine_module
from eventforge.engine import build_game, run_auto_game, validate_agent_reaction_proposal
from eventforge.domain import AgentProfile, AgentReactionContext, AgentReactionProposal, AgentRunState, GeneratedAction, SeedEntity, TurnChoice, ActionCard, FrozenInitialWorld
from eventforge.scenarios import FLASH_CRASH_SCENARIO


class FakeLLM:
    def __init__(self) -> None:
        self.choice_calls = 0
        self.last_available_templates = None
        self.last_choice_prompt = None
        self.profile_calls: list[dict[str, str]] = []
        self.last_summary_prompt = None

    def generate_agent_profile(self, *, entity: SeedEntity, scenario_title: str, world_truth: str) -> AgentProfile:
        self.profile_calls.append(
            {
                "entity_id": entity.id,
                "entity_name": entity.name,
                "scenario_title": scenario_title,
                "world_truth": world_truth,
            }
        )
        return AgentProfile(
            id=entity.id,
            name=entity.name,
            role=entity.role,
            public_goal=entity.public_goal,
            private_fear=f"害怕 {entity.pressure_point}",
            pressure_point=entity.pressure_point,
            voice=f"{entity.name} voice",
            stance=entity.stance,
            trust_in_player=entity.starting_trust,
            influence=entity.influence,
            source_seed_id=entity.id,
        )

    def generate_turn_actions(self, **kwargs: object) -> list[dict[str, str]]:
        self.choice_calls += 1
        self.last_available_templates = kwargs.get("available_templates")
        self.last_choice_prompt = kwargs
        return [
            {"template_id": "statement", "label": "发布证据时间线", "description": "把证据按时间线公开，争取叙事权。"},
            {"template_id": "ama", "label": "开 AMA 接受拷打", "description": "直播回应最尖锐的问题。"},
            {"template_id": "buyback", "label": "短线回购托底", "description": "用国库买回流动性信心。"},
            {"template_id": "freeze_wallet", "label": "冻结争议钱包", "description": "以审计和冻结动作换取制度信任。"},
        ]

    def narrate_turn(self, **_: object) -> str:
        return "llm narration"

    def summarize_world_state(self, **kwargs: object) -> tuple[str, str]:
        self.last_summary_prompt = kwargs
        return (
            "世界总结：市场暂时稳住，但仍然脆弱。",
            "可分享：市场暂时稳住，但交易所仍在观察，社区情绪有所回落。",
        )


class HighImpactOnlyLLM(FakeLLM):
    def generate_turn_actions(self, **kwargs: object) -> list[dict[str, str]]:
        self.choice_calls += 1
        self.last_available_templates = kwargs.get("available_templates")
        return [
            {"template_id": "freeze_wallet", "label": "冻结争议钱包", "description": "立刻冻结争议钱包并提审计。"},
            {"template_id": "buyback", "label": "临时回购托底", "description": "直接动用国库资金稳住价格。"},
            {"template_id": "shift_blame", "label": "把锅甩给外部攻击", "description": "把责任导向外部攻击者。"},
            {"template_id": "silent", "label": "继续沉默", "description": "先不说话，观察市场。"},
        ]


class FrozenBackedScenario:
    def __init__(self) -> None:
        frozen_entity = SeedEntity(
            id="frozen-observer",
            name="Frozen Observer",
            role="observer",
            public_goal="根据冻结世界中的设定行动",
            pressure_point="不想被旧 demo 结构污染",
            starting_trust=61,
            influence=44,
            stance="等待冻结世界的信号",
            details="只存在于 frozen world artifact 中。",
        )
        frozen_world = replace(
            FLASH_CRASH_SCENARIO.to_frozen_world(),
            title="Frozen Crisis",
            player_role="校方",
            objective="根据冻结世界推进局势",
            truth="冻结世界中的关键事实。",
            entities=(frozen_entity,),
            initial_dimensions=(
                ("credibility", 73),
                ("treasury", 57),
                ("pressure", 19),
                ("price", 48),
                ("liquidity", 52),
                ("sell_pressure", 31),
                ("volatility", 26),
                ("community_panic", 29),
                ("rumor_level", 22),
                ("narrative_control", 64),
                ("exchange_trust", 68),
                ("control", 77),
            ),
        )
        self._frozen_world = frozen_world
        self.title = "Legacy Demo Title"
        self.player_role = "legacy-role"
        self.objective = "legacy objective"
        self.truth = "legacy truth"
        self.seed_entities = (
            SeedEntity(
                id="legacy-observer",
                name="Legacy Observer",
                role="legacy",
                public_goal="沿用旧 demo 叙事",
                pressure_point="被替换",
                starting_trust=15,
                influence=20,
                stance="坚持旧世界",
                details="只存在于 legacy scenario 字段中。",
            ),
        )
        self.actions = FLASH_CRASH_SCENARIO.actions
        self.initial_world = FLASH_CRASH_SCENARIO.initial_world

    def to_frozen_world(self):
        return self._frozen_world


def test_initial_world_state_is_explicit_and_crisis_shaped() -> None:
    game = build_game(turns=6, seed=1, llm_client=FakeLLM())

    assert game.initial_state == {
        "credibility": 50,
        "treasury": 60,
        "pressure": 35,
        "price": 42,
        "liquidity": 45,
        "sell_pressure": 68,
        "volatility": 72,
        "community_panic": 70,
        "rumor_level": 64,
        "narrative_control": 32,
        "exchange_trust": 43,
        "control": 51,
    }



def test_build_game_uses_frozen_world_state_and_entities_instead_of_legacy_scenario_fields() -> None:
    llm = FakeLLM()
    scenario = FrozenBackedScenario()

    game = build_game(turns=6, seed=1, llm_client=llm, scenario=scenario)

    assert game.initial_state == scenario.to_frozen_world().initial_dimension_map()
    assert [profile.name for profile in game.agent_profiles] == ["Frozen Observer"]
    assert llm.profile_calls == [
        {
            "entity_id": "frozen-observer",
            "entity_name": "Frozen Observer",
            "scenario_title": "Frozen Crisis",
            "world_truth": "冻结世界中的关键事实。",
        }
    ]



def test_build_game_accepts_frozen_world_without_legacy_scenario_wrapper() -> None:
    llm = FakeLLM()
    scenario = FrozenBackedScenario()
    frozen_world = scenario.to_frozen_world()

    game = build_game(turns=6, seed=1, llm_client=llm, frozen_world=frozen_world)

    assert game.frozen_world == frozen_world
    assert game.initial_state == frozen_world.initial_dimension_map()
    assert [profile.name for profile in game.agent_profiles] == ["Frozen Observer"]
    assert game.available_actions()
    assert llm.profile_calls == [
        {
            "entity_id": "frozen-observer",
            "entity_name": "Frozen Observer",
            "scenario_title": "Frozen Crisis",
            "world_truth": "冻结世界中的关键事实。",
        }
    ]


def test_build_game_prefers_frozen_world_action_grammar_over_legacy_scenario_actions() -> None:
    llm = FakeLLM()
    scenario = FrozenBackedScenario()
    frozen_world = replace(
        scenario.to_frozen_world(),
        action_grammar=replace(
            scenario.to_frozen_world().action_grammar,
            rules=tuple(
                replace(rule, key=f"frozen-{rule.key}", label=f"冻结版 {rule.label}")
                for rule in scenario.to_frozen_world().action_grammar.rules[:4]
            ),
        ),
    )

    world_rule_ids = [rule.key for rule in frozen_world.action_grammar.rules]
    legacy_action_ids = [action.id for action in scenario.actions]
    assert world_rule_ids != legacy_action_ids

    game = build_game(turns=6, seed=1, llm_client=llm, scenario=scenario, frozen_world=frozen_world)

    assert [action.id for action in game.action_templates] == world_rule_ids


def test_generated_material_scenarios_use_frozen_world_synthesized_action_templates() -> None:
    generated_frozen_world = replace(
        FLASH_CRASH_SCENARIO.to_frozen_world(),
        title="校园争议冻结世界",
        player_role="校方",
        objective="稳住校内外冲突升级",
        action_grammar=replace(
            FLASH_CRASH_SCENARIO.to_frozen_world().action_grammar,
            rules=tuple(
                replace(rule, key=f"world-rule-{index}", label=f"世界规则 {index}")
                for index, rule in enumerate(FLASH_CRASH_SCENARIO.to_frozen_world().action_grammar.rules[:4], start=1)
            ),
        ),
    )

    class GeneratedMaterialScenario:
        actions = ()

        def to_frozen_world(self):
            return generated_frozen_world

    llm = FakeLLM()
    game = build_game(turns=6, seed=1, llm_client=llm, scenario=GeneratedMaterialScenario())

    assert [action.id for action in game.action_templates] == [f"world-rule-{index}" for index in range(1, 5)]


def test_runtime_prompts_and_report_use_frozen_world_metadata() -> None:

    llm = FakeLLM()
    scenario = FrozenBackedScenario()
    game = build_game(turns=6, seed=3, llm_client=llm, scenario=scenario)
    game.begin_turn()

    action = game.available_actions()[0]
    game.apply_choice(TurnChoice(action=action, reason="test"))
    game.build_world_report()

    assert llm.last_choice_prompt["scenario_title"] == "Frozen Crisis"
    assert llm.last_choice_prompt["player_role"] == "校方"
    assert llm.last_choice_prompt["player_objective"] == "根据冻结世界推进局势"
    assert llm.last_summary_prompt["scenario_title"] == "Frozen Crisis"
    assert llm.last_summary_prompt["player_role"] == "校方"



def test_begin_turn_creates_agent_driven_event_and_updates_state() -> None:
    game = build_game(turns=6, seed=7, llm_client=FakeLLM())

    event = game.begin_turn()

    assert event is not None
    assert event.actor_id in {agent.id for agent in game.agent_profiles}
    assert event.actor_name
    assert event.summary
    assert game.state.turn_index == 0
    assert any(event.state_delta.get(key, 0) != 0 for key in ("pressure", "rumor_level", "sell_pressure", "exchange_trust", "community_panic", "liquidity", "price"))



def test_available_actions_are_generated_by_llm_each_turn() -> None:
    llm = FakeLLM()
    game = build_game(turns=6, seed=3, llm_client=llm)
    game.begin_turn()

    actions = game.available_actions()

    assert llm.choice_calls == 1
    assert len(actions) == 4
    assert all(isinstance(action, GeneratedAction) for action in actions)
    assert actions[0].label == "发布证据时间线"
    assert actions[0].id == "statement"
    assert actions[0].upside_dimensions
    assert actions[0].downside_dimensions
    assert actions[0].commitment_tier in {"low", "medium", "high"}
    assert llm.last_available_templates is not None
    assert llm.last_choice_prompt is not None
    assert llm.last_choice_prompt["player_objective"]
    assert llm.last_choice_prompt["decision_focus"]
    assert llm.last_choice_prompt["action_context"].action_grammar.menu_size == 4
    assert llm.last_choice_prompt["action_context"].situation.urgent_dimensions
    assert all("impact_tier" in template for template in llm.last_available_templates)
    assert all("upside_axes" in template for template in llm.last_available_templates)
    assert all("downside_axes" in template for template in llm.last_available_templates)
    assert all(template["upside_axes"] for template in llm.last_available_templates)
    assert all(template["downside_axes"] for template in llm.last_available_templates)



def test_generated_choice_copy_gets_explicit_tradeoff_metadata() -> None:
    game = build_game(turns=6, seed=3, llm_client=FakeLLM())
    game.begin_turn()

    action = game.available_actions()[0]

    assert action.rationale
    assert action.upside_magnitude
    assert action.downside_magnitude
    assert set(action.upside_magnitude) == set(action.upside_dimensions)
    assert set(action.downside_magnitude) == set(action.downside_dimensions)


def test_generated_choice_copy_does_not_duplicate_existing_tradeoff_suffix() -> None:
    game = build_game(turns=6, seed=3, llm_client=FakeLLM())

    description = game._normalize_action_description(
        base=game.scenario.actions[0],
        description="把证据按时间线公开，争取叙事权。（+叙事控制/+平台信任 / -传言水平/-压力）",
    )

    assert description.count("（+") == 1



def test_available_actions_enforce_impact_diversity_when_llm_returns_only_heavy_moves() -> None:
    game = build_game(turns=6, seed=3, llm_client=HighImpactOnlyLLM())
    game.begin_turn()

    actions = game.available_actions()
    tiers = [action.commitment_tier for action in actions]

    assert len(actions) == 4
    assert len(set(action.id for action in actions)) == 4
    assert "low" in tiers
    assert "medium" in tiers
    assert sum(1 for tier in tiers if tier == "high") <= 2



def test_decision_focus_reflects_current_state_gaps() -> None:
    llm = FakeLLM()
    game = build_game(turns=6, seed=3, llm_client=llm)
    game.state.exchange_trust = 18
    game.state.community_panic = 88
    game.state.liquidity = 24
    game.begin_turn()

    game.available_actions()

    focus = llm.last_choice_prompt["decision_focus"]
    assert focus[0]["axis"] == "exchange_trust"
    assert {item["axis"] for item in focus[:3]} >= {"exchange_trust", "community_panic", "liquidity"}



def test_apply_choice_returns_distinct_agent_reactions() -> None:
    game = build_game(turns=6, seed=3, llm_client=FakeLLM())
    game.begin_turn()
    action = next(action for action in game.available_actions() if action.id == "statement")

    resolution = game.apply_choice(TurnChoice(action=action, reason="test"))

    assert len(resolution.agent_reactions) == len(game.agent_profiles)
    names = {reaction.actor_name for reaction in resolution.agent_reactions}
    assert "AshSignals" in names
    assert "Onyx Exchange" in names
    kol = next(reaction for reaction in resolution.agent_reactions if reaction.actor_name == "AshSignals")
    exchange = next(reaction for reaction in resolution.agent_reactions if reaction.actor_name == "Onyx Exchange")
    assert kol.summary != exchange.summary



def test_score_action_uses_generated_action_metadata_without_template_lookup() -> None:
    game = build_game(turns=6, seed=3, llm_client=FakeLLM())
    game.action_template_map = {}
    action = GeneratedAction(
        id="world-authored-audit",
        label="公开审计框架",
        description="先公开审计框架和处理边界。",
        rationale="用控制权和平台信任换取喘息空间，但会抬高即时压力。",
        upside_dimensions=("control", "exchange_trust"),
        downside_dimensions=("pressure", "volatility"),
        upside_magnitude={"control": 9, "exchange_trust": 7},
        downside_magnitude={"pressure": 6, "volatility": 4},
        cost_types=("legal",),
        affected_entities=("exchange-onyx",),
        commitment_tier="medium",
        tags=("audit",),
    )

    score = game._score_action(action)

    assert isinstance(score, int)
    assert score > 0



def test_score_action_rewards_reductions_on_lower_is_better_dimensions() -> None:
    game = build_game(turns=6, seed=3, llm_client=FakeLLM())
    game.action_template_map = {}
    original_focus = engine_module.decision_focus_from_state
    engine_module.decision_focus_from_state = lambda state: []
    try:
        action = GeneratedAction(
            id="steady-the-room",
            label="稳住场面",
            description="先压住恐慌和波动，再争取回应窗口。",
            rationale="降低压力和波动，代价是消耗一点控制空间。",
            upside_dimensions=("pressure", "volatility"),
            downside_dimensions=("control",),
            upside_magnitude={"pressure": 8, "volatility": 6},
            downside_magnitude={"control": 2},
            cost_types=("public",),
            affected_entities=("community-watchers",),
            commitment_tier="low",
            tags=("stabilize",),
        )

        score = game._score_action(action)
    finally:
        engine_module.decision_focus_from_state = original_focus

    assert score > 0



def test_apply_choice_uses_generated_action_metadata_without_template_lookup() -> None:
    game = build_game(turns=6, seed=3, llm_client=FakeLLM())
    game.begin_turn()
    game.action_template_map = {}
    game._generate_agent_reactions = lambda action: []
    game._apply_secondary_world_rules = lambda action, reactions: None
    before = game.snapshot_state()
    action = GeneratedAction(
        id="freeze_wallet",
        label="冻结争议钱包并启动审计",
        description="先冻结争议钱包，同时启动审计说明。",
        rationale="提升控制、平台信任与叙事控制，但会推高压力并消耗资源。",
        upside_dimensions=("control", "exchange_trust", "narrative_control"),
        downside_dimensions=("pressure", "treasury"),
        upside_magnitude={"control": 8, "exchange_trust": 6, "narrative_control": 5},
        downside_magnitude={"pressure": 7, "treasury": 4},
        cost_types=("legal",),
        affected_entities=("exchange-onyx",),
        commitment_tier="high",
        tags=("audit",),
    )

    resolution = game.apply_choice(TurnChoice(action=action, reason="test"))

    assert resolution.action_id == "freeze_wallet"
    assert game.state.control == before["control"] + 8
    assert game.state.exchange_trust == before["exchange_trust"] + 6
    assert game.state.narrative_control == before["narrative_control"] + 5
    assert game.state.pressure == before["pressure"] + 7
    assert game.state.treasury == before["treasury"] - 4
    assert game.state.truth_public is True
    assert "wallet_frozen" in game.state.flags



def test_apply_choice_clamps_generated_action_magnitudes_by_commitment_tier() -> None:
    game = build_game(turns=6, seed=3, llm_client=FakeLLM())
    game.begin_turn()
    game.action_template_map = {}
    game._generate_agent_reactions = lambda action: []
    game._apply_secondary_world_rules = lambda action, reactions: None
    before = game.snapshot_state()
    action = GeneratedAction(
        id="bounded-world-action",
        label="过载动作",
        description="尝试用极端动作直接压穿局面。",
        rationale="大幅推动控制，但会明显抬高压力。",
        upside_dimensions=("control",),
        downside_dimensions=("pressure",),
        upside_magnitude={"control": 99},
        downside_magnitude={"pressure": 99},
        cost_types=("public",),
        affected_entities=("exchange-onyx",),
        commitment_tier="high",
        tags=("stabilize",),
    )

    game.apply_choice(TurnChoice(action=action, reason="test"))

    assert game.state.control == before["control"] + 10
    assert game.state.pressure == before["pressure"] + 10



def test_validate_agent_reaction_proposal_clamps_unknown_fields_and_updates_memory() -> None:
    game = build_game(turns=6, seed=3, llm_client=FakeLLM())
    state = AgentRunState(
        agent_id="onyx-exchange",
        agent_name="Onyx Exchange",
        role="exchange",
        stance="谨慎观望",
        current_objective="暂不升级风控",
        scalar_state={
            "trust_in_player": 95,
            "pressure_load": 10,
            "escalation_drive": 5,
            "public_alignment": 40,
        },
    )
    context = AgentReactionContext(
        world_id=game.frozen_world.world_id,
        world_title=game.frozen_world.title,
        turn_index=2,
        turns_total=6,
        player_role=game.scenario.player_role,
        player_objective=game.scenario.objective,
        chosen_action_id="statement",
        chosen_action_label="发布证据时间线",
        chosen_action_summary="公开时间线，试图换回叙事控制，但会提升制度压力。",
        current_dimensions=game.state.to_dimension_map(),
        urgent_dimensions=("exchange_trust",),
        unstable_dimensions=("exchange_trust",),
        dominant_tensions=("平台风控",),
        acting_agent=state,
        relevant_entities=("project-founder",),
        recent_turn_summaries=("上一回合社区持续质疑",),
        boundaries=game.frozen_world.reaction_boundaries,
    )
    proposal = AgentReactionProposal(
        summary="平台决定先给窗口，但会保留更严厉的后手。",
        stance="暂时配合",
        updated_objective="争取更多补充材料",
        scalar_deltas={"trust_in_player": 50, "pressure_load": -50, "unknown_axis": 9},
        relationship_deltas={
            "project-founder": {"alignment": 30, "visibility": -80, "unknown_field": 5},
            "ignored-target": {"strain": 10},
        },
        dimension_impacts={"exchange_trust": 99, "control": -99, "unknown_dimension": 4},
        follow_on_hooks=("institutional_freeze", "bad-hook", "public-procedure-scrutiny"),
    )

    updated_state, result = validate_agent_reaction_proposal(
        context=context,
        proposal=proposal,
        known_entities={"project-founder"},
    )

    assert updated_state.scalar_state["trust_in_player"] == 100
    assert updated_state.scalar_state["pressure_load"] == 0
    assert "unknown_axis" not in result.applied_scalar_deltas
    assert result.applied_relationship_deltas == {"project-founder": {"alignment": 18, "visibility": -18}}
    assert result.applied_dimension_impacts == {"exchange_trust": 12, "control": -12}
    assert result.triggered_hooks == ("institutional_freeze",)
    assert updated_state.triggered_hooks == ("institutional_freeze",)
    assert updated_state.memories[-1].action_id == "statement"
    assert updated_state.memories[-1].salience > 0



def test_apply_choice_updates_agent_run_state_bridge_from_existing_reaction_logic() -> None:
    game = build_game(turns=6, seed=3, llm_client=FakeLLM())
    game.begin_turn()
    action = next(action for action in game.available_actions() if action.id == "statement")

    before = game.agent_run_states["exchange-onyx"]

    resolution = game.apply_choice(TurnChoice(action=action, reason="test"))

    after = game.agent_run_states["exchange-onyx"]

    assert len(resolution.agent_reactions) == len(game.agent_profiles)
    assert after.agent_id == "exchange-onyx"
    assert after.scalar_state["trust_in_player"] >= before.scalar_state["trust_in_player"]
    assert after.memories[-1].action_id == "statement"
    assert after.memories[-1].turn_index == resolution.turn_number



def test_validate_agent_reaction_proposal_respects_zero_hook_and_memory_caps() -> None:
    game = build_game(turns=6, seed=3, llm_client=FakeLLM())
    base_boundaries = game.frozen_world.reaction_boundaries
    assert base_boundaries is not None
    zero_cap_boundaries = base_boundaries.__class__(
        scalar_axes=base_boundaries.scalar_axes,
        max_relationship_delta_per_turn=base_boundaries.max_relationship_delta_per_turn,
        max_dimension_impacts_per_reaction=base_boundaries.max_dimension_impacts_per_reaction,
        max_dimension_delta_per_reaction=base_boundaries.max_dimension_delta_per_reaction,
        max_relationship_updates_per_reaction=base_boundaries.max_relationship_updates_per_reaction,
        max_hooks_per_reaction=0,
        memory_limit=0,
        allowed_hook_tags=base_boundaries.allowed_hook_tags,
    )
    state = AgentRunState(
        agent_id="onyx-exchange",
        agent_name="Onyx Exchange",
        role="exchange",
        stance="谨慎观望",
        current_objective="暂不升级风控",
        scalar_state={
            "trust_in_player": 60,
            "pressure_load": 30,
            "escalation_drive": 20,
            "public_alignment": 50,
        },
    )
    context = AgentReactionContext(
        world_id=game.frozen_world.world_id,
        world_title=game.frozen_world.title,
        turn_index=2,
        turns_total=6,
        player_role=game.frozen_world.player_role,
        player_objective=game.frozen_world.objective,
        chosen_action_id="statement",
        chosen_action_label="发布证据时间线",
        chosen_action_summary="公开时间线，试图换回叙事控制，但会提升制度压力。",
        current_dimensions=game.state.to_dimension_map(),
        urgent_dimensions=("exchange_trust",),
        unstable_dimensions=("exchange_trust",),
        dominant_tensions=("平台风控",),
        acting_agent=state,
        relevant_entities=("project-founder",),
        recent_turn_summaries=("上一回合社区持续质疑",),
        boundaries=zero_cap_boundaries,
    )
    proposal = AgentReactionProposal(
        summary="平台决定先给窗口，但会保留更严厉的后手。",
        stance="暂时配合",
        updated_objective="争取更多补充材料",
        scalar_deltas={"trust_in_player": 8},
        relationship_deltas={},
        dimension_impacts={"exchange_trust": 5},
        follow_on_hooks=("institutional_freeze",),
    )

    updated_state, result = validate_agent_reaction_proposal(
        context=context,
        proposal=proposal,
        known_entities={"project-founder"},
    )

    assert result.triggered_hooks == ()
    assert updated_state.triggered_hooks == ()
    assert updated_state.memories == ()



def test_run_auto_game_returns_shareable_world_report_with_ending_score() -> None:
    game, report = run_auto_game(turns=10, seed=11, llm_client=FakeLLM())

    assert len(game.history) == 10
    assert report.share_text
    assert report.summary.startswith("世界总结")
    assert report.initial_state != report.final_state
    assert "control" in report.diff
    assert "turns" in report.timeline_markdown
    assert report.final_state["price"] >= 0
    assert report.final_state["price"] <= 100
    assert isinstance(report.ending_score, int)
    assert 0 <= report.ending_score <= 100
    assert report.ending_id
    assert report.ending_title
    assert report.ending_description



def test_world_state_endings_map_to_score_bands() -> None:
    game = build_game(turns=6, seed=1, llm_client=FakeLLM())

    bleak = game._build_ending_from_state(
        {
            "credibility": 20,
            "treasury": 15,
            "pressure": 95,
            "price": 18,
            "liquidity": 20,
            "sell_pressure": 90,
            "volatility": 88,
            "community_panic": 92,
            "rumor_level": 86,
            "narrative_control": 18,
            "exchange_trust": 15,
            "control": 20,
        }
    )
    strong = game._build_ending_from_state(
        {
            "credibility": 88,
            "treasury": 52,
            "pressure": 40,
            "price": 80,
            "liquidity": 78,
            "sell_pressure": 22,
            "volatility": 18,
            "community_panic": 16,
            "rumor_level": 18,
            "narrative_control": 90,
            "exchange_trust": 92,
            "control": 89,
        }
    )

    assert bleak["ending_score"] < strong["ending_score"]
    assert bleak["ending_id"] != strong["ending_id"]
    assert bleak["ending_title"]
    assert strong["ending_title"]



def test_world_report_uses_frozen_world_local_ending_labels() -> None:
    llm = FakeLLM()
    frozen_world = replace(
        FLASH_CRASH_SCENARIO.to_frozen_world(),
        ending_bands=(
            FLASH_CRASH_SCENARIO.to_frozen_world().ending_bands[0],
            FLASH_CRASH_SCENARIO.to_frozen_world().ending_bands[1],
            FLASH_CRASH_SCENARIO.to_frozen_world().ending_bands[2],
            FLASH_CRASH_SCENARIO.to_frozen_world().ending_bands[3],
            replace(
                FLASH_CRASH_SCENARIO.to_frozen_world().ending_bands[-1],
                ending_id="world-local-collapse",
                label="校誉尽失",
                description="这条世界线使用自己的四字结局标签。",
            ),
        ),
    )
    game = build_game(turns=6, seed=1, llm_client=llm, frozen_world=frozen_world)
    game.state.credibility = 20
    game.state.treasury = 15
    game.state.pressure = 95
    game.state.price = 18
    game.state.liquidity = 20
    game.state.sell_pressure = 90
    game.state.volatility = 88
    game.state.community_panic = 92
    game.state.rumor_level = 86
    game.state.narrative_control = 18
    game.state.exchange_trust = 15
    game.state.control = 20

    report = game.build_world_report()

    assert report.ending_id == "world-local-collapse"
    assert report.ending_title == "校誉尽失"
    assert report.ending_description == "这条世界线使用自己的四字结局标签。"



def test_extreme_pressure_triggers_anomaly_flag_and_warning() -> None:
    game = build_game(turns=6, seed=3, llm_client=FakeLLM())
    game.state.pressure = 92
    game.begin_turn()
    action = next(action for action in game.available_actions() if action.id == "statement")

    resolution = game.apply_choice(TurnChoice(action=action, reason="test"))

    assert "pressure_breakdown" in resolution.state_snapshot.flags
    assert any("压力异常" in bullet for bullet in resolution.bullet_points)
    assert resolution.state_snapshot.control < 52



def test_freeze_wallet_publishes_truth_and_sets_flag() -> None:
    game = build_game(turns=6, seed=5, llm_client=FakeLLM())
    game.begin_turn()
    action = next(action for action in game.available_actions() if action.id == "freeze_wallet")

    resolution = game.apply_choice(TurnChoice(action=action, reason="test"))

    assert resolution.state_snapshot.truth_public is True
    assert "wallet_frozen" in resolution.state_snapshot.flags



def test_buyback_becomes_unavailable_when_treasury_is_too_low() -> None:
    game = build_game(turns=6, seed=9, llm_client=FakeLLM())
    game.state.treasury = 10

    actions = game.available_actions()

    assert all(action.id != "buyback" for action in actions)
