from eventforge.domain import ScenarioBlueprint, SeedEntity
from eventforge.llm import OpenAICompatibleLLM


class SequencedTransport:
    def __init__(self, payloads: list[dict]) -> None:
        self.payloads = payloads
        self.calls = []

    def create_chat_completion(self, **kwargs: object) -> dict:
        self.calls.append(kwargs)
        return self.payloads.pop(0)



def test_llm_profile_generation_maps_json_response() -> None:
    entity = SeedEntity(
        id="community-1",
        name="Mira",
        role="community",
        public_goal="save trust",
        pressure_point="continued lying",
        starting_trust=50,
        influence=55,
        stance="uneasy",
        details="core admin",
    )
    transport = SequencedTransport(
        [
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"private_fear":"被当成共犯","voice":"温和但有底线","stance":"愿意先帮你稳群","trust_in_player":61,"influence":58}'
                        }
                    }
                ]
            }
        ]
    )
    client = OpenAICompatibleLLM(
        base_url="https://example.invalid/v1",
        api_key="test-key",
        model="test-model",
        transport=transport,
    )

    profile = client.generate_agent_profile(entity=entity, scenario_title="demo", world_truth="truth")

    assert profile.private_fear == "被当成共犯"
    assert profile.voice == "温和但有底线"
    assert profile.trust_in_player == 61
    assert profile.influence == 58



def test_llm_turn_action_generation_maps_json_response() -> None:
    transport = SequencedTransport(
        [
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"actions":[{"template_id":"statement","label":"发布证据时间线","description":"公开时间线和证据。"},{"template_id":"ama","label":"开 AMA 正面回应","description":"直播回答尖锐问题。"},{"template_id":"buyback","label":"短线回购托底","description":"拿国库稳住价格。"},{"template_id":"freeze_wallet","label":"冻结争议钱包","description":"冻结并配合审计。"}]}'
                        }
                    }
                ]
            }
        ]
    )
    client = OpenAICompatibleLLM(
        base_url="https://example.invalid/v1",
        api_key="test-key",
        model="test-model",
        transport=transport,
    )

    actions = client.generate_turn_actions(
        scenario_title="demo",
        player_role="founder",
        player_objective="保住控制权并稳住市场叙事",
        state_summary={"control": 50},
        decision_focus=[{"axis": "control", "urgency": 10, "desired_direction": "up"}],
        available_templates=[
            {
                "id": "statement",
                "label": "发布长文澄清",
                "impact_tier": "medium",
                "impact_cost": 8,
                "upside_axes": ["narrative_control"],
                "downside_axes": ["pressure"],
            }
        ],
    )

    assert len(actions) == 4
    assert actions[0]["template_id"] == "statement"
    assert actions[0]["label"] == "发布证据时间线"



def test_llm_scenario_blueprint_generation_maps_json_response() -> None:
    transport = SequencedTransport(
        [
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"title":"蓝屏之后","premise":"一次更新导致全球服务中断。","player_role":"平台负责人","player_secret":"你知道真正问题来自内部发布流程。","objective":"在信任耗尽前稳住关键合作方。","opponent":"扩散中的 outage 叙事","audience":["客户","媒体","合作伙伴"],"truth":"错误更新触发连锁故障。","opening_event":{"headline":"全球服务大面积中断","summary":"多个行业同时受影响。","severity":81},"entities":[{"id":"ops-media","name":"OpsWatch","role":"kol","public_goal":"抢先定义事故叙事","pressure_point":"误判风险","starting_trust":22,"influence":78,"stance":"怀疑平台在隐瞒","details":"持续追踪事故时间线"},{"id":"enterprise-alpha","name":"Alpha Bank","role":"whale","public_goal":"尽快恢复核心服务","pressure_point":"停机损失扩大","starting_trust":31,"influence":74,"stance":"观望并准备切换供应商","details":"关键企业客户"}],"initial_world":{"credibility":41,"treasury":63,"pressure":72,"price":49,"liquidity":46,"sell_pressure":58,"volatility":66,"community_panic":69,"rumor_level":62,"narrative_control":28,"exchange_trust":35,"control":44}}'
                        }
                    }
                ]
            }
        ]
    )
    client = OpenAICompatibleLLM(
        base_url="https://example.invalid/v1",
        api_key="test-key",
        model="test-model",
        transport=transport,
    )

    blueprint = client.generate_scenario_blueprint(
        source_material="一次错误更新导致多行业服务中断",
        entity_cap=8,
        selected_player_role="平台负责人",
    )

    assert isinstance(blueprint, ScenarioBlueprint)
    assert blueprint.title == "蓝屏之后"
    assert len(blueprint.entities) == 2
    assert blueprint.initial_world.pressure == 72
    assert blueprint.opening_event.severity == 81
    system_prompt = transport.calls[0]["messages"][0]["content"]
    assert "relative to the chosen player_role" in system_prompt
    assert "playable_roles" in system_prompt
    assert "neutral stakeholder groups" in system_prompt
    assert "derive entity roles from the material itself" in system_prompt
    assert "at least 3 core world metrics materially different" in system_prompt
    user_payload = transport.calls[0]["messages"][1]["content"]
    assert "平台负责人" in user_payload
    assert "selected_player_role" in user_payload
    assert blueprint.playable_roles == ("平台负责人",)



def test_llm_scenario_blueprint_generation_tolerates_loose_real_world_output() -> None:
    transport = SequencedTransport(
        [
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"title":"Blue Screen Cascade","premise":"A faulty update triggers global outages.","player_role":"exchange","player_secret":"You delayed stricter continuity requirements.","objective":"Stabilize market confidence.","opponent":"Fast-moving rumor ecosystem.","audience":"Listed companies, institutional traders, regulators, affected enterprises","truth":"This is not a hack but a bad update.","opening_event":"At market open, multiple companies report outages and social media trends cyberattack.","entities":[{"id":"e1","name":"Falcon Vendor","role":"market_maker","description":"Security supplier behind the faulty update."},{"id":"e2","name":"Media Swarm","role":"kol","description":"Narrative accelerators driving blame."}],"initial_world":{"credibility":44,"treasury":68,"pressure":86,"price":57,"liquidity":62,"sell_pressure":78,"volatility":83,"community_panic":74,"rumor_level":81,"narrative_control":29,"exchange_trust":48,"control":35}}'
                        }
                    }
                ]
            }
        ]
    )
    client = OpenAICompatibleLLM(
        base_url="https://example.invalid/v1",
        api_key="test-key",
        model="test-model",
        transport=transport,
    )

    blueprint = client.generate_scenario_blueprint(
        source_material="一次错误更新造成全球 IT 中断",
        entity_cap=8,
    )

    assert blueprint.audience
    assert blueprint.opening_event.headline
    assert blueprint.opening_event.severity == 70
    assert blueprint.entities[0].public_goal
    assert blueprint.entities[0].pressure_point
    assert blueprint.entities[0].details



def test_llm_world_summary_maps_json_response() -> None:
    transport = SequencedTransport(
        [
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"summary":"世界总结：叙事暂时稳住，但交易所仍在观察。","share_text":"可分享：市场从恐慌转向观望，项目控制权小幅回升。"}'
                        }
                    }
                ]
            }
        ]
    )
    client = OpenAICompatibleLLM(
        base_url="https://example.invalid/v1",
        api_key="test-key",
        model="test-model",
        transport=transport,
    )

    summary, share_text = client.summarize_world_state(
        scenario_title="demo",
        player_role="founder",
        initial_state={"control": 50},
        final_state={"control": 60},
        diff={"control": 10},
        timeline=["t1", "t2"],
    )

    assert summary.startswith("世界总结")
    assert share_text.startswith("可分享")
