from eventforge.engine import action_impact_profile, build_game, run_auto_game, validate_agent_reaction_proposal
from eventforge.domain import AgentProfile, AgentReactionContext, AgentReactionProposal, AgentRunState, SeedEntity, TurnChoice, ActionCard


class FakeLLM:
    def __init__(self) -> None:
        self.choice_calls = 0
        self.last_available_templates = None
        self.last_choice_prompt = None

    def generate_agent_profile(self, *, entity: SeedEntity, scenario_title: str, world_truth: str) -> AgentProfile:
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

    def summarize_world_state(self, **_: object) -> tuple[str, str]:
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
    assert all(isinstance(action, ActionCard) for action in actions)
    assert actions[0].label == "发布证据时间线"
    assert actions[0].id == "statement"
    assert "+" in actions[0].description
    assert "-" in actions[0].description
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



def test_generated_choice_copy_gets_explicit_tradeoff_suffix() -> None:
    game = build_game(turns=6, seed=3, llm_client=FakeLLM())
    game.begin_turn()

    action = game.available_actions()[0]

    assert "+" in action.description
    assert "-" in action.description
    assert "叙事控制" in action.description or "交易所信任" in action.description


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
    tiers = [action_impact_profile(action)["impact_tier"] for action in actions]

    assert len(actions) == 4
    assert len(set(action.id for action in actions)) == 4
    assert "low" in tiers
    assert "medium" in tiers
    assert sum(1 for tier in tiers if tier == "extreme") <= 1



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
