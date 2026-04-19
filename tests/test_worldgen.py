from eventforge.domain import ScenarioBlueprint, SeedEntity, WorldEvent, WorldState
from eventforge.engine import build_game
from eventforge.worldgen import (
    build_scenario_from_material,
    inspect_material_seed,
    repair_initial_world_state,
    validate_initial_world_state,
)


class FakeWorldgenLLM:
    def __init__(self, *, entity_count: int = 5) -> None:
        self.entity_count = entity_count
        self.last_selected_player_role = None

    def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
        self.last_selected_player_role = selected_player_role
        entities = []
        role_cycle = ["kol", "whale", "market_maker", "community", "exchange"]
        for index in range(self.entity_count):
            entities.append(
                SeedEntity(
                    id=f"entity-{index}",
                    name=f"Entity {index}",
                    role=role_cycle[index % len(role_cycle)],
                    public_goal=f"goal {index}",
                    pressure_point=f"pressure {index}",
                    starting_trust=30 + (index % 20),
                    influence=40 + (index % 40),
                    stance="watching",
                    details=f"details {index}",
                )
            )
        return ScenarioBlueprint(
            title="测试危机",
            premise=f"基于材料生成：{source_material[:20]}",
            player_role="项目负责人",
            player_secret="你知道内部真正问题。",
            objective="保住局面并修复叙事。",
            opponent="扩散中的负面叙事",
            audience=("用户", "媒体", "合作方"),
            truth="内部问题已经暴露。",
            opening_event=WorldEvent(headline="危机爆发", summary="事件开始发酵。", severity=70),
            entities=tuple(entities),
            initial_world=WorldState(
                credibility=8,
                treasury=5,
                pressure=96,
                price=10,
                liquidity=12,
                sell_pressure=95,
                volatility=93,
                community_panic=94,
                rumor_level=90,
                narrative_control=10,
                exchange_trust=12,
                control=14,
            ),
        )

    def generate_agent_profile(self, *, entity: SeedEntity, scenario_title: str, world_truth: str):
        from eventforge.domain import AgentProfile

        return AgentProfile(
            id=entity.id,
            name=entity.name,
            role=entity.role,
            public_goal=entity.public_goal,
            private_fear=entity.pressure_point,
            pressure_point=entity.pressure_point,
            voice="steady",
            stance=entity.stance,
            trust_in_player=entity.starting_trust,
            influence=entity.influence,
            source_seed_id=entity.id,
        )


def test_build_scenario_from_material_caps_entities() -> None:
    scenario = build_scenario_from_material(
        source_material="重大事故材料",
        llm_client=FakeWorldgenLLM(entity_count=40),
        entity_cap=12,
    )

    assert len(scenario.seed_entities) == 12


def test_generated_initial_world_is_repaired_into_playable_band() -> None:
    repaired = repair_initial_world_state(
        WorldState(
            credibility=5,
            treasury=3,
            pressure=99,
            price=4,
            liquidity=6,
            sell_pressure=98,
            volatility=96,
            community_panic=97,
            rumor_level=95,
            narrative_control=6,
            exchange_trust=4,
            control=8,
        )
    )

    validation = validate_initial_world_state(repaired)
    assert validation.is_playable is True


def test_unrepaired_dead_world_is_not_playable() -> None:
    validation = validate_initial_world_state(
        WorldState(
            credibility=5,
            treasury=3,
            pressure=99,
            price=4,
            liquidity=6,
            sell_pressure=98,
            volatility=96,
            community_panic=97,
            rumor_level=95,
            narrative_control=6,
            exchange_trust=4,
            control=8,
        )
    )

    assert validation.is_playable is False
    assert validation.reasons


def test_build_game_uses_generated_initial_world() -> None:
    scenario = build_scenario_from_material(
        source_material="平台服务事故和舆论危机",
        llm_client=FakeWorldgenLLM(entity_count=8),
        entity_cap=8,
    )

    game = build_game(turns=6, seed=1, llm_client=FakeWorldgenLLM(entity_count=8), scenario=scenario)

    assert game.initial_state["pressure"] == scenario.initial_world.pressure
    assert game.initial_state["control"] == scenario.initial_world.control


def test_build_scenario_normalizes_player_role_and_neutralizes_polarized_groups() -> None:
    class PolarizedWorldgenLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            return ScenarioBlueprint(
                title="校园风波",
                premise="事件进入校内外对冲阶段。",
                player_role="校方核心决策者",
                player_secret="内部流程存在瑕疵。",
                objective="稳住校方公信力。",
                opponent="失控的舆论发酵",
                audience=("学生", "校友", "公众"),
                truth="多方都在争夺定义权。",
                opening_event=WorldEvent(headline="热搜再起", summary="讨论再度发酵。", severity=76),
                entities=(
                    SeedEntity(
                        id="supporters",
                        name="支持杨景媛的声音",
                        role="学生群体",
                        public_goal="推动对本人有利的叙事",
                        pressure_point="被认为立场偏颇",
                        starting_trust=40,
                        influence=55,
                        stance="supportive",
                        details="集中转发、强调个人处境",
                    ),
                    SeedEntity(
                        id="opponents",
                        name="反对杨景媛的声音",
                        role="学生群体",
                        public_goal="要求更严厉追责",
                        pressure_point="被认为网暴",
                        starting_trust=20,
                        influence=65,
                        stance="hostile",
                        details="持续质疑处理过程",
                    ),
                    SeedEntity(
                        id="school",
                        name="武汉大学校方",
                        role="校方",
                        public_goal="控制事件升级",
                        pressure_point="公信力下滑",
                        starting_trust=35,
                        influence=80,
                        stance="defensive",
                        details="需要面对学生与公众双重压力",
                    ),
                ),
                initial_world=WorldState(
                    credibility=44,
                    treasury=52,
                    pressure=76,
                    price=48,
                    liquidity=45,
                    sell_pressure=62,
                    volatility=68,
                    community_panic=71,
                    rumor_level=73,
                    narrative_control=31,
                    exchange_trust=37,
                    control=39,
                ),
            )

    scenario = build_scenario_from_material(
        source_material="武汉大学相关舆论材料",
        llm_client=PolarizedWorldgenLLM(entity_count=3),
        entity_cap=8,
    )

    assert scenario.player_role == "校方"
    community_entities = [entity for entity in scenario.seed_entities if entity.name == "围绕杨景媛事件的相关人群"]
    assert len(community_entities) == 1
    assert community_entities[0].role == "学生群体"
    assert "不同立场" in community_entities[0].details
    school_entity = next(entity for entity in scenario.seed_entities if entity.name == "武汉大学校方")
    assert school_entity.role == "校方"


def test_build_scenario_normalizes_verbose_institution_viewpoint_labels_and_prioritizes_matching_entities() -> None:
    class VerboseInstitutionRoleLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            chosen_role = selected_player_role or "港口危机协调负责人"
            return ScenarioBlueprint(
                title="断桥与封港",
                premise="多方都在争抢复航和问责节奏。",
                player_role=chosen_role,
                player_secret="复航窗口和责任边界并不同步。",
                objective="稳住复航与公众信心。",
                opponent="对位阵营",
                audience=("公众", "物流客户", "监管部门"),
                truth="不同机构都想把成本转移给别人。",
                opening_event=WorldEvent(headline="主航道封锁", summary="复航时间表和责任叙事同时失控。", severity=82),
                entities=(
                    SeedEntity("port", "港口运营体系与航道工程承包链", "港口运营体系", "推动复航", "工程延误", 56, 88, "defensive", "执行导向的现场主体"),
                    SeedEntity("state", "州政府与地方应急体系", "州政府应急体系", "稳住公共秩序", "政治问责", 61, 90, "strongly defensive", "负责统筹跨部门响应"),
                    SeedEntity("shipping", "航运集团与船东联合体", "航运集团", "控制赔偿与停航损失", "责任扩大", 31, 84, "under fire", "直接承担事故与停摆压力"),
                ),
                initial_world=WorldState(
                    credibility=49,
                    treasury=60,
                    pressure=83,
                    price=45,
                    liquidity=49,
                    sell_pressure=67,
                    volatility=73,
                    community_panic=77,
                    rumor_level=74,
                    narrative_control=36,
                    exchange_trust=43,
                    control=48,
                ),
                playable_roles=("港口危机协调负责人", "州政府应急负责人", "航运集团风险负责人"),
            )

    scenario = build_scenario_from_material(
        source_material="巴尔的摩港复航材料",
        llm_client=VerboseInstitutionRoleLLM(entity_count=3),
        entity_cap=8,
        selected_player_role="州政府应急负责人",
    )

    assert scenario.player_role == "州政府"
    assert scenario.playable_roles == ("州政府", "港口", "航运集团")
    assert scenario.seed_entities[0].name == "州政府与地方应急体系"
    assert scenario.seed_entities[1].name == "港口运营体系与航道工程承包链"


def test_inspection_resolves_counterparts_for_verbose_institution_viewpoints() -> None:
    class VerboseInstitutionInspectionLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            chosen_role = selected_player_role or "港口危机协调负责人"
            worldview = {
                "港口危机协调负责人": dict(credibility=54, pressure=84, narrative_control=40, control=52, treasury=61, liquidity=50, exchange_trust=44, community_panic=76),
                "港口": dict(credibility=54, pressure=84, narrative_control=40, control=52, treasury=61, liquidity=50, exchange_trust=44, community_panic=76),
                "州政府应急负责人": dict(credibility=58, pressure=81, narrative_control=44, control=57, treasury=63, liquidity=54, exchange_trust=48, community_panic=73),
                "州政府": dict(credibility=58, pressure=81, narrative_control=44, control=57, treasury=63, liquidity=54, exchange_trust=48, community_panic=73),
                "航运集团风险负责人": dict(credibility=29, pressure=92, narrative_control=21, control=24, treasury=41, liquidity=35, exchange_trust=28, community_panic=86),
                "航运集团": dict(credibility=29, pressure=92, narrative_control=21, control=24, treasury=41, liquidity=35, exchange_trust=28, community_panic=86),
            }[chosen_role]
            return ScenarioBlueprint(
                title="断桥与封港",
                premise="视角检查应该能识别冗长机构标签背后的真实对位角色。",
                player_role=chosen_role,
                player_secret="不同机构掌握不同恢复路径。",
                objective="争取复航节奏控制权。",
                opponent="对位阵营",
                audience=("公众", "物流客户", "监管部门"),
                truth="问责叙事和复航节奏彼此缠绕。",
                opening_event=WorldEvent(headline="主航道封锁", summary="多方都在抢第一轮定义权。", severity=82),
                entities=(
                    SeedEntity("port", "港口运营体系与航道工程承包链", "港口运营体系", "推动复航", "工程延误", 56, 88, "defensive", "执行导向的现场主体"),
                    SeedEntity("state", "州政府与地方应急体系", "州政府应急体系", "稳住公共秩序", "政治问责", 61, 90, "strongly defensive", "负责统筹跨部门响应"),
                    SeedEntity("shipping", "航运集团与船东联合体", "航运集团", "控制赔偿与停航损失", "责任扩大", 31, 84, "under fire", "直接承担事故与停摆压力"),
                ),
                initial_world=WorldState(
                    credibility=worldview["credibility"],
                    treasury=worldview["treasury"],
                    pressure=worldview["pressure"],
                    price=45,
                    liquidity=worldview["liquidity"],
                    sell_pressure=68,
                    volatility=74,
                    community_panic=worldview["community_panic"],
                    rumor_level=75,
                    narrative_control=worldview["narrative_control"],
                    exchange_trust=worldview["exchange_trust"],
                    control=worldview["control"],
                ),
                playable_roles=("港口危机协调负责人", "州政府应急负责人", "航运集团风险负责人"),
            )

    inspection = inspect_material_seed(
        source_material="巴尔的摩港复航材料",
        llm_client=VerboseInstitutionInspectionLLM(entity_count=3),
        entity_cap=8,
        selected_player_role="州政府应急负责人",
    )

    assert inspection.selected_role == "州政府"
    assert inspection.baseline_role == "州政府"
    assert inspection.playable_roles == ("州政府", "港口", "航运集团")
    selected_card = inspection.viewpoints[0]
    comparison_card = inspection.viewpoints[-1]
    assert selected_card.player_entity == "州政府与地方应急体系"
    assert selected_card.relationship_summary == "州政府与地方应急体系（州政府应急体系） ↔ 港口运营体系与航道工程承包链（港口运营体系）"
    assert comparison_card.role == "航运集团"
    assert comparison_card.primary_counterpart == "州政府与地方应急体系"
    assert inspection.comparison_summary.startswith("航运集团：航运集团与船东联合体（航运集团） ↔ 州政府与地方应急体系（州政府应急体系）")


def test_build_scenario_preserves_material_defined_roles() -> None:
    class MaterialRoleWorldgenLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            return ScenarioBlueprint(
                title="实名舆情局",
                premise="不同实体来自不同材料位置。",
                player_role="校方",
                player_secret="你知道完整流程。",
                objective="稳住局面。",
                opponent="外部舆论发酵",
                audience=("学生", "公众"),
                truth="各方都在争夺定义权。",
                opening_event=WorldEvent(headline="冲突升级", summary="新的讨论被点燃。", severity=70),
                entities=(
                    SeedEntity(
                        id="school",
                        name="武汉大学校方",
                        role="校方",
                        public_goal="恢复公信力",
                        pressure_point="程序解释不足",
                        starting_trust=45,
                        influence=88,
                        stance="defensive",
                        details="校内正式回应主体",
                    ),
                    SeedEntity(
                        id="students",
                        name="在校学生群体",
                        role="学生群体",
                        public_goal="获得可信解释",
                        pressure_point="信息不透明",
                        starting_trust=36,
                        influence=66,
                        stance="split",
                        details="校内讨论持续扩散",
                    ),
                    SeedEntity(
                        id="media",
                        name="主流媒体与教育口记者群",
                        role="媒体",
                        public_goal="追踪事实链条",
                        pressure_point="信息缺口过大",
                        starting_trust=30,
                        influence=80,
                        stance="probing",
                        details="会持续追问学校处理流程",
                    ),
                ),
                initial_world=WorldState(
                    credibility=40,
                    treasury=55,
                    pressure=74,
                    price=45,
                    liquidity=47,
                    sell_pressure=63,
                    volatility=65,
                    community_panic=68,
                    rumor_level=70,
                    narrative_control=33,
                    exchange_trust=42,
                    control=44,
                ),
            )

    scenario = build_scenario_from_material(
        source_material="武汉大学相关舆论材料",
        llm_client=MaterialRoleWorldgenLLM(entity_count=3),
        entity_cap=8,
    )

    assert [entity.role for entity in scenario.seed_entities] == ["校方", "学生群体", "媒体"]


def test_build_scenario_can_target_selected_player_role_with_different_initial_state() -> None:
    class MultiRoleWorldgenLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            self.last_selected_player_role = selected_player_role
            chosen_role = selected_player_role or "校方"
            if chosen_role == "杨景媛":
                initial_world = WorldState(
                    credibility=29,
                    treasury=36,
                    pressure=92,
                    price=41,
                    liquidity=52,
                    sell_pressure=71,
                    volatility=78,
                    community_panic=82,
                    rumor_level=88,
                    narrative_control=45,
                    exchange_trust=34,
                    control=22,
                )
            else:
                initial_world = WorldState(
                    credibility=43,
                    treasury=62,
                    pressure=81,
                    price=34,
                    liquidity=56,
                    sell_pressure=68,
                    volatility=73,
                    community_panic=69,
                    rumor_level=74,
                    narrative_control=28,
                    exchange_trust=41,
                    control=64,
                )
            return ScenarioBlueprint(
                title="武汉大学杨景媛事件",
                premise="直接冲突当事人可以作为玩家选择。",
                player_role=chosen_role,
                player_secret="双方都握有不能完全公开的信息。",
                objective="在舆论失控前争取主动。",
                opponent="对立叙事与外部放大",
                audience=("学生", "公众", "媒体"),
                truth="同一事件对不同当事人的起始局面并不相同。",
                opening_event=WorldEvent(headline="事件再上热搜", summary="新的爆料和旧截图一起扩散。", severity=78),
                entities=(
                    SeedEntity(
                        id="school",
                        name="武汉大学校方",
                        role="校方",
                        public_goal="恢复程序公信力",
                        pressure_point="回应节奏滞后",
                        starting_trust=40,
                        influence=88,
                        stance="defensive",
                        details="学校治理与回应主体",
                    ),
                    SeedEntity(
                        id="yang",
                        name="杨景媛",
                        role="杨景媛",
                        public_goal="维护个人叙事与行动正当性",
                        pressure_point="持续被放在公共审判中",
                        starting_trust=34,
                        influence=82,
                        stance="embattled",
                        details="直接冲突当事人之一",
                    ),
                    SeedEntity(
                        id="students",
                        name="在校学生群体",
                        role="学生群体",
                        public_goal="获得可信解释",
                        pressure_point="信息碎片化",
                        starting_trust=38,
                        influence=68,
                        stance="split",
                        details="内部观点分裂但高度关注",
                    ),
                ),
                initial_world=initial_world,
            )

    llm = MultiRoleWorldgenLLM(entity_count=3)
    school_scenario = build_scenario_from_material(
        source_material="武汉大学杨景媛事件",
        llm_client=llm,
        entity_cap=8,
        selected_player_role="校方",
    )
    yang_scenario = build_scenario_from_material(
        source_material="武汉大学杨景媛事件",
        llm_client=llm,
        entity_cap=8,
        selected_player_role="杨景媛",
    )

    assert school_scenario.player_role == "校方"
    assert yang_scenario.player_role == "杨景媛"
    assert school_scenario.initial_world.control != yang_scenario.initial_world.control
    assert school_scenario.initial_world.pressure != yang_scenario.initial_world.pressure
    assert yang_scenario.initial_world.pressure > school_scenario.initial_world.pressure
    assert llm.last_selected_player_role == "杨景媛"


def test_build_scenario_exposes_playable_roles() -> None:
    class PlayableRoleWorldgenLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            return ScenarioBlueprint(
                title="武汉大学杨景媛事件",
                premise="直接冲突双方都可被选择。",
                player_role=selected_player_role or "校方",
                player_secret="双方都掌握部分未公开信息。",
                objective="争取主动权。",
                opponent="失控舆论",
                audience=("学生", "公众"),
                truth="同一事件有多个可玩的直接冲突当事人。",
                opening_event=WorldEvent(headline="热搜升级", summary="讨论持续发酵。", severity=80),
                entities=(
                    SeedEntity("school", "武汉大学校方", "校方", "恢复秩序", "回应滞后", 45, 90, "defensive", "学校治理主体"),
                    SeedEntity("yang", "杨景媛", "杨景媛", "维护个人叙事", "持续被围观审判", 36, 85, "embattled", "直接冲突当事人"),
                ),
                initial_world=WorldState(credibility=42, treasury=55, pressure=80, price=40, liquidity=50, sell_pressure=65, volatility=70, community_panic=71, rumor_level=74, narrative_control=35, exchange_trust=41, control=48),
                playable_roles=("校方", "杨景媛"),
            )

    scenario = build_scenario_from_material(
        source_material="武汉大学杨景媛事件",
        llm_client=PlayableRoleWorldgenLLM(entity_count=2),
        entity_cap=8,
    )

    assert scenario.playable_roles == ("校方", "杨景媛")


def test_build_scenario_calibrates_role_relative_world_when_raw_initial_state_matches() -> None:
    class SameWorldMultiRoleLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            chosen_role = selected_player_role or "校方"
            return ScenarioBlueprint(
                title="校园冲突",
                premise="两个直接冲突当事人都可被选择。",
                player_role=chosen_role,
                player_secret="不同角色掌握的事实不一样。",
                objective="抢在叙事定型前稳住局面。",
                opponent="对立叙事",
                audience=("学生", "公众", "媒体"),
                truth="同一事件对不同当事人意味着不同的起始处境。",
                opening_event=WorldEvent(headline="争议升温", summary="校内外都在持续扩散。", severity=75),
                entities=(
                    SeedEntity("school", "武汉大学校方", "校方", "恢复程序公信力", "回应过慢", 44, 90, "defensive", "制度性回应主体"),
                    SeedEntity("yang", "杨景媛", "杨景媛", "维护个人叙事", "持续承受公共审判", 24, 78, "embattled", "直接冲突个人当事人"),
                    SeedEntity("students", "在校学生群体", "学生群体", "获得可信解释", "信息碎片化", 38, 70, "split", "内部意见高度分裂"),
                ),
                initial_world=WorldState(
                    credibility=41,
                    treasury=55,
                    pressure=78,
                    price=46,
                    liquidity=50,
                    sell_pressure=67,
                    volatility=72,
                    community_panic=74,
                    rumor_level=76,
                    narrative_control=36,
                    exchange_trust=39,
                    control=44,
                ),
                playable_roles=("校方", "杨景媛"),
            )

    llm = SameWorldMultiRoleLLM(entity_count=3)
    school = build_scenario_from_material(
        source_material="武汉大学杨景媛事件",
        llm_client=llm,
        entity_cap=8,
        selected_player_role="校方",
    )
    yang = build_scenario_from_material(
        source_material="武汉大学杨景媛事件",
        llm_client=llm,
        entity_cap=8,
        selected_player_role="杨景媛",
    )

    differing_metrics = [
        key
        for key in ("control", "credibility", "pressure", "community_panic", "narrative_control")
        if getattr(school.initial_world, key) != getattr(yang.initial_world, key)
    ]
    assert len(differing_metrics) >= 3
    assert school.initial_world.control > yang.initial_world.control
    assert school.initial_world.credibility > yang.initial_world.credibility
    assert school.initial_world.pressure < yang.initial_world.pressure


def test_inspect_material_seed_builds_viewpoint_cards_for_each_role() -> None:
    class InspectableMultiRoleLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            chosen_role = selected_player_role or "校方"
            control = 62 if chosen_role == "校方" else 28
            pressure = 79 if chosen_role == "校方" else 91
            credibility = 43 if chosen_role == "校方" else 25
            return ScenarioBlueprint(
                title="武汉大学杨景媛事件",
                premise="多视角种子需要可比较的开局剖面。",
                player_role=chosen_role,
                player_secret="不同视角都只能看到部分事实。",
                objective="争取定义权。",
                opponent="对立叙事",
                audience=("学生", "公众"),
                truth="视角切换会改变初始资源与压力。",
                opening_event=WorldEvent(headline="事件再升温", summary="新的截图和旧争议一起扩散。", severity=77),
                entities=(
                    SeedEntity("school", "武汉大学校方", "校方", "恢复秩序", "回应滞后", 44, 90, "defensive", "学校治理主体"),
                    SeedEntity("yang", "杨景媛", "杨景媛", "维护个人叙事", "公共审判", 28, 82, "embattled", "直接冲突当事人"),
                    SeedEntity("students", "在校学生群体", "学生群体", "获得解释", "信息碎片化", 36, 68, "split", "高度关注"),
                ),
                initial_world=WorldState(
                    credibility=credibility,
                    treasury=52,
                    pressure=pressure,
                    price=42,
                    liquidity=50,
                    sell_pressure=67,
                    volatility=72,
                    community_panic=75,
                    rumor_level=78,
                    narrative_control=48 if chosen_role == "杨景媛" else 31,
                    exchange_trust=37,
                    control=control,
                ),
                playable_roles=("校方", "杨景媛"),
            )

    inspection = inspect_material_seed(
        source_material="武汉大学杨景媛事件",
        llm_client=InspectableMultiRoleLLM(entity_count=3),
        entity_cap=8,
    )

    assert inspection.playable_roles == ("校方", "杨景媛")
    assert inspection.baseline_role == "校方"
    assert [card.role for card in inspection.viewpoints] == ["校方", "杨景媛"]
    school_card = inspection.viewpoints[0]
    yang_card = inspection.viewpoints[1]
    assert school_card.metrics["control"] > yang_card.metrics["control"]
    assert school_card.metrics["pressure"] < yang_card.metrics["pressure"]
    assert school_card.summary.startswith(f"控制权 {school_card.metrics['control']}")
    assert yang_card.summary.startswith(f"控制权 {yang_card.metrics['control']}")
    assert school_card.metric_deltas == {"control": 0, "pressure": 0, "credibility": 0, "narrative_control": 0}
    assert yang_card.metric_deltas["control"] < 0
    assert yang_card.metric_deltas["pressure"] > 0
    assert school_card.player_entity == "武汉大学校方"
    assert yang_card.player_entity == "杨景媛"
    assert school_card.player_entity_role == "校方"
    assert yang_card.player_entity_role == "杨景媛"
    assert school_card.primary_counterpart == "杨景媛"
    assert yang_card.primary_counterpart == "武汉大学校方"
    assert school_card.primary_counterpart_role == "杨景媛"
    assert yang_card.primary_counterpart_role == "校方"
    assert yang_card.delta_summary.startswith("控制权")
    assert "武汉大学校方" in school_card.key_entities


def test_selected_player_role_is_promoted_to_front_of_playable_roles() -> None:
    class OrderedPlayableRolesLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            return ScenarioBlueprint(
                title="平台争议",
                premise="多方都可切入。",
                player_role=selected_player_role or "平台",
                player_secret="内部都知道关键节点。",
                objective="争取保住定义权。",
                opponent="直接冲突对手",
                audience=("用户", "公众"),
                truth="同一事件可从多个角色游玩。",
                opening_event=WorldEvent(headline="争议爆发", summary="讨论蔓延。", severity=74),
                entities=(
                    SeedEntity("platform", "某平台", "平台", "保住公信力", "流程漏洞", 42, 86, "defensive", "平台主体"),
                    SeedEntity("creator", "当事创作者", "创作者", "维护个人叙事", "持续被围攻", 38, 82, "embattled", "直接冲突方"),
                ),
                initial_world=WorldState(credibility=42, treasury=57, pressure=81, price=45, liquidity=51, sell_pressure=63, volatility=69, community_panic=70, rumor_level=72, narrative_control=34, exchange_trust=39, control=47),
                playable_roles=("平台", "创作者", "公众观察者"),
            )

    scenario = build_scenario_from_material(
        source_material="平台争议材料",
        llm_client=OrderedPlayableRolesLLM(entity_count=2),
        entity_cap=8,
        selected_player_role="创作者",
    )

    assert scenario.playable_roles == ("创作者", "平台", "公众观察者")


def test_build_scenario_deduplicates_equivalent_person_role_labels() -> None:
    class EquivalentRoleLabelsLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            return ScenarioBlueprint(
                title="校园风波",
                premise="同一当事人的不同叫法不应变成重复视角。",
                player_role="杨景媛本人",
                player_secret="不同叫法本质上指向同一个人。",
                objective="避免重复视角污染比较输出。",
                opponent="校方",
                audience=("学生", "公众"),
                truth="人名后缀不应该制造伪多角色。",
                opening_event=WorldEvent(headline="舆论升温", summary="多个版本的当事人称呼同时出现。", severity=76),
                entities=(
                    SeedEntity("school", "武汉大学校方", "校方", "恢复秩序", "回应迟缓", 42, 88, "defensive", "机构主体"),
                    SeedEntity("yang", "杨景媛", "杨景媛", "维护个人叙事", "持续承压", 34, 82, "embattled", "直接冲突当事人"),
                ),
                initial_world=WorldState(credibility=28, treasury=48, pressure=90, price=45, liquidity=45, sell_pressure=67, volatility=73, community_panic=80, rumor_level=82, narrative_control=42, exchange_trust=33, control=27),
                playable_roles=("校方", "杨景媛本人", "杨景媛"),
            )

    scenario = build_scenario_from_material(
        source_material="武汉大学杨景媛事件",
        llm_client=EquivalentRoleLabelsLLM(entity_count=2),
        entity_cap=8,
        selected_player_role="杨景媛",
    )

    assert scenario.player_role == "杨景媛"
    assert scenario.playable_roles == ("杨景媛", "校方")


def test_build_scenario_promotes_player_and_counterpart_entities_for_selected_viewpoint() -> None:
    class OrderedEntitiesLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            return ScenarioBlueprint(
                title="平台争议",
                premise="平台与创作者直接对撞。",
                player_role=selected_player_role or "平台",
                player_secret="双方都知道流程里有灰区。",
                objective="争取先发解释权。",
                opponent="对位角色与扩散人群",
                audience=("用户", "公众"),
                truth="同一材料下玩家应先看到自己和主要对位。",
                opening_event=WorldEvent(headline="争议升级", summary="双方都在抢定义权。", severity=76),
                entities=(
                    SeedEntity("users", "普通用户", "用户群体", "获得解释", "信息不足", 36, 66, "split", "外围放大器"),
                    SeedEntity("platform", "某平台", "平台", "保住公信力", "流程漏洞", 42, 86, "defensive", "平台主体"),
                    SeedEntity("creator", "当事创作者", "创作者", "维护个人叙事", "持续被围攻", 38, 82, "embattled", "直接冲突方"),
                ),
                initial_world=WorldState(credibility=42, treasury=57, pressure=81, price=45, liquidity=51, sell_pressure=63, volatility=69, community_panic=70, rumor_level=72, narrative_control=34, exchange_trust=39, control=47),
                playable_roles=("平台", "创作者"),
            )

    scenario = build_scenario_from_material(
        source_material="平台争议材料",
        llm_client=OrderedEntitiesLLM(entity_count=3),
        entity_cap=8,
        selected_player_role="创作者",
    )

    assert [entity.role for entity in scenario.seed_entities[:3]] == ["创作者", "平台", "用户群体"]
    assert [entity.name for entity in scenario.seed_entities[:2]] == ["当事创作者", "某平台"]


def test_build_scenario_for_symmetric_conflict_parties_still_diverges_by_viewpoint() -> None:
    class SymmetricConflictLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            chosen_role = selected_player_role or "公司"
            return ScenarioBlueprint(
                title="品牌合作翻车",
                premise="公司与艺人团队互相指责。",
                player_role=chosen_role,
                player_secret="双方都握有片段证据。",
                objective="避免自己成为唯一责任方。",
                opponent="对手阵营与失控舆论",
                audience=("粉丝", "公众", "媒体"),
                truth="合同解释和执行过程都存在问题。",
                opening_event=WorldEvent(headline="合作争议升级", summary="双方声明互相打脸。", severity=79),
                entities=(
                    SeedEntity("company", "品牌公司", "公司", "保住品牌信誉", "承认失误会触发更大追责", 40, 84, "under fire", "商业合作主体"),
                    SeedEntity("artist", "艺人团队", "艺人团队", "保住个人口碑", "公开证据会引发反噬", 40, 84, "under fire", "直接冲突另一方"),
                    SeedEntity("media", "娱乐记者群", "媒体", "追逐更多细节", "被抢跑", 35, 70, "probing", "放大双方表态"),
                ),
                initial_world=WorldState(
                    credibility=42,
                    treasury=56,
                    pressure=80,
                    price=45,
                    liquidity=49,
                    sell_pressure=64,
                    volatility=71,
                    community_panic=73,
                    rumor_level=75,
                    narrative_control=36,
                    exchange_trust=40,
                    control=46,
                ),
                playable_roles=("公司", "艺人团队"),
            )

    llm = SymmetricConflictLLM(entity_count=3)
    company = build_scenario_from_material(
        source_material="品牌合作翻车材料",
        llm_client=llm,
        entity_cap=8,
        selected_player_role="公司",
    )
    artist = build_scenario_from_material(
        source_material="品牌合作翻车材料",
        llm_client=llm,
        entity_cap=8,
        selected_player_role="艺人团队",
    )

    differing_metrics = [
        key
        for key in ("control", "credibility", "pressure", "community_panic", "narrative_control")
        if getattr(company.initial_world, key) != getattr(artist.initial_world, key)
    ]
    assert len(differing_metrics) >= 3
    assert company.initial_world != artist.initial_world


def test_build_scenario_for_identical_noninstitutional_conflict_parties_still_diverges_by_viewpoint() -> None:
    class IdenticalConflictLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            chosen_role = selected_player_role or "甲方团队"
            return ScenarioBlueprint(
                title="双人争议",
                premise="双方都不是机构，也都拥有几乎一样的原始资源。",
                player_role=chosen_role,
                player_secret="双方都各握有一半证据。",
                objective="避免自己被舆论钉死。",
                opponent="对位团队与围观扩散",
                audience=("公众", "媒体"),
                truth="对称冲突也必须呈现不同的主观开局。",
                opening_event=WorldEvent(headline="双边声明互呛", summary="两边都说自己才是受害者。", severity=78),
                entities=(
                    SeedEntity("party-a", "甲方团队", "甲方团队", "维护自身版本", "公开全部证据会反噬", 40, 80, "under fire", "冲突一方"),
                    SeedEntity("party-b", "乙方团队", "乙方团队", "维护自身版本", "公开全部证据会反噬", 40, 80, "under fire", "冲突另一方"),
                    SeedEntity("crowd", "围观群众", "公众", "获取更多细节", "被误导", 40, 70, "watching", "围观放大器"),
                ),
                initial_world=WorldState(
                    credibility=42,
                    treasury=56,
                    pressure=80,
                    price=45,
                    liquidity=49,
                    sell_pressure=64,
                    volatility=71,
                    community_panic=73,
                    rumor_level=75,
                    narrative_control=36,
                    exchange_trust=40,
                    control=46,
                ),
                playable_roles=("甲方团队", "乙方团队"),
            )

    llm = IdenticalConflictLLM(entity_count=3)
    party_a = build_scenario_from_material(
        source_material="双人争议材料",
        llm_client=llm,
        entity_cap=8,
        selected_player_role="甲方团队",
    )
    party_b = build_scenario_from_material(
        source_material="双人争议材料",
        llm_client=llm,
        entity_cap=8,
        selected_player_role="乙方团队",
    )

    differing_metrics = [
        key
        for key in ("control", "credibility", "pressure", "community_panic", "narrative_control")
        if getattr(party_a.initial_world, key) != getattr(party_b.initial_world, key)
    ]
    assert len(differing_metrics) >= 3
    assert party_a.initial_world != party_b.initial_world


def test_build_scenario_calibrates_operational_slack_for_institutional_viewpoints() -> None:
    class InstitutionalSlackLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            chosen_role = selected_player_role or "校方"
            return ScenarioBlueprint(
                title="校园争议",
                premise="机构方与个人方在相同材料下应拥有不同的起手腾挪空间。",
                player_role=chosen_role,
                player_secret="双方都掌握部分未公开事实。",
                objective="先撑住第一轮叙事冲击。",
                opponent="对位角色与放大舆论",
                audience=("学生", "公众", "媒体"),
                truth="机构与个人的资源松弛度不该完全相同。",
                opening_event=WorldEvent(headline="争议冲顶", summary="同一批截图引发两边同时承压。", severity=80),
                entities=(
                    SeedEntity("school", "武汉大学校方", "校方", "恢复程序公信力", "回应迟缓", 42, 90, "defensive", "机构回应主体"),
                    SeedEntity("yang", "杨景媛", "杨景媛", "维护个人叙事", "持续被围观审判", 42, 82, "embattled", "直接冲突个人方"),
                    SeedEntity("students", "在校学生群体", "学生群体", "获得可信解释", "信息不透明", 38, 70, "split", "关注事件走向"),
                ),
                initial_world=WorldState(
                    credibility=42,
                    treasury=56,
                    pressure=80,
                    price=45,
                    liquidity=49,
                    sell_pressure=64,
                    volatility=71,
                    community_panic=73,
                    rumor_level=75,
                    narrative_control=36,
                    exchange_trust=40,
                    control=46,
                ),
                playable_roles=("校方", "杨景媛"),
            )

    llm = InstitutionalSlackLLM(entity_count=3)
    school = build_scenario_from_material(
        source_material="校园争议材料",
        llm_client=llm,
        entity_cap=8,
        selected_player_role="校方",
    )
    yang = build_scenario_from_material(
        source_material="校园争议材料",
        llm_client=llm,
        entity_cap=8,
        selected_player_role="杨景媛",
    )

    assert school.initial_world.treasury > yang.initial_world.treasury
    assert school.initial_world.liquidity > yang.initial_world.liquidity
    assert school.initial_world.exchange_trust > yang.initial_world.exchange_trust


def test_inspect_material_seed_marks_selected_viewpoint_and_baseline_summary() -> None:
    class SelectedInspectionLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            chosen_role = selected_player_role or "平台"
            return ScenarioBlueprint(
                title="平台争议",
                premise="需要更清晰地比较视角。",
                player_role=chosen_role,
                player_secret="双方都只掌握部分证据。",
                objective="赢下第一轮定义权。",
                opponent="对位角色",
                audience=("用户", "公众"),
                truth="比较输出必须指出谁是当前选择与基准。",
                opening_event=WorldEvent(headline="舆论对撞", summary="双方都在抢时间。", severity=74),
                entities=(
                    SeedEntity("users", "普通用户", "用户群体", "获得解释", "信息缺口", 35, 60, "split", "外围观察者"),
                    SeedEntity("platform", "某平台", "平台", "恢复秩序", "流程问题", 44, 86, "defensive", "机构主体"),
                    SeedEntity("creator", "当事创作者", "创作者", "保护个人叙事", "持续承压", 33, 82, "embattled", "直接冲突方"),
                ),
                initial_world=WorldState(
                    credibility=45 if chosen_role == "平台" else 28,
                    treasury=58,
                    pressure=78 if chosen_role == "平台" else 90,
                    price=45,
                    liquidity=50,
                    sell_pressure=65,
                    volatility=71,
                    community_panic=70 if chosen_role == "平台" else 82,
                    rumor_level=74,
                    narrative_control=30 if chosen_role == "平台" else 46,
                    exchange_trust=41,
                    control=60 if chosen_role == "平台" else 26,
                ),
                playable_roles=("平台", "创作者"),
            )

    inspection = inspect_material_seed(
        source_material="平台争议材料",
        llm_client=SelectedInspectionLLM(entity_count=3),
        entity_cap=8,
        selected_player_role="创作者",
    )

    assert inspection.selected_role == "创作者"
    assert inspection.baseline_role == "创作者"
    assert inspection.baseline_summary.startswith("控制权")
    selected_card = inspection.viewpoints[0]
    other_card = inspection.viewpoints[1]
    assert selected_card.is_selected is True
    assert selected_card.is_baseline is True
    assert other_card.is_selected is False
    assert other_card.is_baseline is False
    assert selected_card.key_entities[:2] == ("当事创作者", "某平台")


def test_inspect_material_seed_exposes_contrast_score_and_focus_metrics() -> None:
    class ContrastInspectionLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            chosen_role = selected_player_role or "平台"
            return ScenarioBlueprint(
                title="平台争议",
                premise="比较输出应直接告诉我们最重要的差异轴。",
                player_role=chosen_role,
                player_secret="双方都掌握部分证据。",
                objective="争取第一轮定义权。",
                opponent="对位角色",
                audience=("用户", "公众"),
                truth="差异焦点应该能一眼看清。",
                opening_event=WorldEvent(headline="舆论对撞", summary="双方都在抢时间。", severity=74),
                entities=(
                    SeedEntity("platform", "某平台", "平台", "恢复秩序", "流程问题", 44, 86, "defensive", "机构主体"),
                    SeedEntity("creator", "当事创作者", "创作者", "保护个人叙事", "持续承压", 33, 82, "embattled", "直接冲突方"),
                    SeedEntity("users", "普通用户", "用户群体", "获得解释", "信息缺口", 35, 60, "split", "外围观察者"),
                ),
                initial_world=WorldState(
                    credibility=45 if chosen_role == "平台" else 28,
                    treasury=58 if chosen_role == "平台" else 44,
                    pressure=78 if chosen_role == "平台" else 90,
                    price=45,
                    liquidity=54 if chosen_role == "平台" else 39,
                    sell_pressure=65,
                    volatility=71,
                    community_panic=70 if chosen_role == "平台" else 82,
                    rumor_level=74,
                    narrative_control=30 if chosen_role == "平台" else 46,
                    exchange_trust=43 if chosen_role == "平台" else 31,
                    control=60 if chosen_role == "平台" else 26,
                ),
                playable_roles=("平台", "创作者"),
            )

    inspection = inspect_material_seed(
        source_material="平台争议材料",
        llm_client=ContrastInspectionLLM(entity_count=3),
        entity_cap=8,
        selected_player_role="创作者",
    )

    selected_card = inspection.viewpoints[0]
    other_card = inspection.viewpoints[1]
    assert selected_card.contrast_score == 0
    assert selected_card.focus_metrics == ()
    assert other_card.contrast_score > 0
    assert other_card.focus_metrics == ("control", "credibility", "pressure")
    assert inspection.comparison_role == "平台"
    assert inspection.comparison_focus.startswith("控制权")
    assert inspection.comparison_focus_metrics == ("control", "credibility", "pressure")
    assert inspection.comparison_focus_count >= 2


def test_inspection_chooses_highest_contrast_role_as_primary_comparison() -> None:
    class MultiRoleInspectionLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            chosen_role = selected_player_role or "平台"
            if chosen_role == "品牌方":
                initial_world = WorldState(
                    credibility=36,
                    treasury=52,
                    pressure=84,
                    price=45,
                    liquidity=46,
                    sell_pressure=65,
                    volatility=70,
                    community_panic=75,
                    rumor_level=74,
                    narrative_control=37,
                    exchange_trust=38,
                    control=42,
                )
            elif chosen_role == "创作者":
                initial_world = WorldState(
                    credibility=24,
                    treasury=44,
                    pressure=92,
                    price=45,
                    liquidity=39,
                    sell_pressure=68,
                    volatility=74,
                    community_panic=83,
                    rumor_level=81,
                    narrative_control=49,
                    exchange_trust=31,
                    control=25,
                )
            else:
                initial_world = WorldState(
                    credibility=46,
                    treasury=58,
                    pressure=78,
                    price=45,
                    liquidity=53,
                    sell_pressure=63,
                    volatility=69,
                    community_panic=69,
                    rumor_level=72,
                    narrative_control=32,
                    exchange_trust=42,
                    control=59,
                )
            return ScenarioBlueprint(
                title="平台争议",
                premise="多视角比较应该突出和基准差异最大的对位角色。",
                player_role=chosen_role,
                player_secret="不同角色掌握不同局部真相。",
                objective="抢下第一轮解释权。",
                opponent="对位角色",
                audience=("用户", "公众"),
                truth="不是所有可选视角和基准的差异都一样大。",
                opening_event=WorldEvent(headline="舆论对撞", summary="多方同时发声。", severity=75),
                entities=(
                    SeedEntity("platform", "某平台", "平台", "恢复秩序", "流程问题", 44, 86, "defensive", "机构主体"),
                    SeedEntity("brand", "合作品牌方", "品牌方", "尽快切割风险", "继续沉默会被视为共谋", 39, 78, "under fire", "次级直接冲突方"),
                    SeedEntity("creator", "当事创作者", "创作者", "保护个人叙事", "持续承压", 33, 82, "embattled", "主要直接冲突方"),
                ),
                initial_world=initial_world,
                playable_roles=("平台", "品牌方", "创作者"),
            )

    inspection = inspect_material_seed(
        source_material="平台争议材料",
        llm_client=MultiRoleInspectionLLM(entity_count=3),
        entity_cap=8,
        selected_player_role="平台",
    )

    assert inspection.baseline_role == "平台"
    assert inspection.comparison_role == "创作者"
    assert inspection.comparison_focus_metrics == ("control", "credibility", "pressure")
    assert inspection.viewpoints[1].role == "品牌方"
    assert inspection.viewpoints[2].role == "创作者"


def test_inspect_material_seed_exposes_relationship_summary_and_role_overview() -> None:
    class RelationshipInspectionLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            chosen_role = selected_player_role or "平台"
            return ScenarioBlueprint(
                title="平台争议",
                premise="多角色 seed 需要更容易横向比较。",
                player_role=chosen_role,
                player_secret="双方都藏着一部分证据。",
                objective="先拿到第一轮定义权。",
                opponent="对位角色",
                audience=("用户", "公众"),
                truth="可选视角应该自带简明关系说明。",
                opening_event=WorldEvent(headline="多方发声", summary="每个角色都在找自己的落点。", severity=73),
                entities=(
                    SeedEntity("platform", "某平台", "平台", "恢复秩序", "流程缺口", 46, 87, "defensive", "机构主体"),
                    SeedEntity("creator", "当事创作者", "创作者", "保护个人叙事", "持续承压", 32, 84, "embattled", "直接冲突方"),
                    SeedEntity("brand", "合作品牌方", "品牌方", "切断风险敞口", "继续沉默会被视为共谋", 37, 72, "under fire", "次级冲突方"),
                ),
                initial_world=WorldState(
                    credibility=45 if chosen_role == "平台" else 31,
                    treasury=57 if chosen_role == "平台" else 43,
                    pressure=77 if chosen_role == "平台" else 88,
                    price=45,
                    liquidity=52 if chosen_role == "平台" else 39,
                    sell_pressure=64,
                    volatility=70,
                    community_panic=68 if chosen_role == "平台" else 81,
                    rumor_level=73,
                    narrative_control=29 if chosen_role == "平台" else 48,
                    exchange_trust=42 if chosen_role == "平台" else 31,
                    control=61 if chosen_role == "平台" else 27,
                ),
                playable_roles=("平台", "创作者", "品牌方"),
            )

    inspection = inspect_material_seed(
        source_material="平台争议材料",
        llm_client=RelationshipInspectionLLM(entity_count=3),
        entity_cap=8,
        selected_player_role="创作者",
    )

    selected_card = inspection.viewpoints[0]
    assert selected_card.relationship_summary == "当事创作者（创作者） ↔ 某平台（平台）"
    assert inspection.selected_summary.startswith("创作者：当事创作者（创作者） ↔ 某平台（平台）")
    assert inspection.role_overview[0].startswith("创作者：当事创作者（创作者） ↔ 某平台（平台）")
    assert any(line.startswith("平台：某平台（平台） ↔ 当事创作者（创作者）") for line in inspection.role_overview)


def test_build_scenario_amplifies_stance_relative_gap_for_direct_conflict_roles() -> None:
    class StanceConflictLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            chosen_role = selected_player_role or "甲方团队"
            return ScenarioBlueprint(
                title="双边对撞",
                premise="同一材料下，直接冲突双方的主观开局应该稳定分化。",
                player_role=chosen_role,
                player_secret="双方都握有未公开聊天记录。",
                objective="别让自己在第一轮被定性。",
                opponent="对位团队",
                audience=("公众", "媒体"),
                truth="直接冲突双方虽然原始资源接近，但体感压力不同。",
                opening_event=WorldEvent(headline="双方连发声明", summary="同一时间窗内两边同时开麦。", severity=79),
                entities=(
                    SeedEntity("party-a", "甲方团队", "甲方团队", "守住合作版本", "继续沉默会坐实责任", 42, 80, "defensive", "相对有组织的一方"),
                    SeedEntity("party-b", "乙方团队", "乙方团队", "守住合作版本", "持续承压且无法统一口径", 42, 80, "embattled", "更被动的一方"),
                    SeedEntity("audience", "行业观察者", "观察者", "看清细节", "被两边误导", 36, 58, "watching", "外围放大器"),
                ),
                initial_world=WorldState(
                    credibility=42,
                    treasury=56,
                    pressure=80,
                    price=45,
                    liquidity=49,
                    sell_pressure=64,
                    volatility=71,
                    community_panic=73,
                    rumor_level=75,
                    narrative_control=36,
                    exchange_trust=40,
                    control=46,
                ),
                playable_roles=("甲方团队", "乙方团队"),
            )

    llm = StanceConflictLLM(entity_count=3)
    party_a = build_scenario_from_material(
        source_material="双边对撞材料",
        llm_client=llm,
        entity_cap=8,
        selected_player_role="甲方团队",
    )
    party_b = build_scenario_from_material(
        source_material="双边对撞材料",
        llm_client=llm,
        entity_cap=8,
        selected_player_role="乙方团队",
    )

    assert party_a.initial_world.control >= party_b.initial_world.control + 8
    assert party_a.initial_world.pressure + 8 <= party_b.initial_world.pressure
    assert party_a.initial_world.community_panic + 6 <= party_b.initial_world.community_panic
    assert party_a.initial_world.narrative_control + 6 <= party_b.initial_world.narrative_control


def test_inspect_material_seed_exposes_structured_role_overview_cards() -> None:
    class StructuredOverviewLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            chosen_role = selected_player_role or "创作者"
            return ScenarioBlueprint(
                title="平台争议",
                premise="inspection 应提供比纯字符串更稳定的多视角概览数据。",
                player_role=chosen_role,
                player_secret="不同角色持有不同证据片段。",
                objective="争取第一轮定义权。",
                opponent="主要对位角色",
                audience=("用户", "公众"),
                truth="角色对比不仅用于打印，也应该能稳定驱动上层 UI。",
                opening_event=WorldEvent(headline="舆论继续扩散", summary="多个阵营都在加码发声。", severity=76),
                entities=(
                    SeedEntity("platform", "某平台", "平台", "恢复秩序", "流程问题", 44, 86, "defensive", "机构主体"),
                    SeedEntity("creator", "当事创作者", "创作者", "保护个人叙事", "持续承压", 33, 82, "embattled", "主要直接冲突方"),
                    SeedEntity("brand", "合作品牌方", "品牌方", "控制风险敞口", "被视为共谋", 39, 72, "under fire", "次级冲突方"),
                ),
                initial_world=WorldState(
                    credibility=28 if chosen_role == "创作者" else 45,
                    treasury=44 if chosen_role == "创作者" else 57,
                    pressure=90 if chosen_role == "创作者" else 78,
                    price=45,
                    liquidity=39 if chosen_role == "创作者" else 52,
                    sell_pressure=66,
                    volatility=72,
                    community_panic=82 if chosen_role == "创作者" else 69,
                    rumor_level=76,
                    narrative_control=46 if chosen_role == "创作者" else 31,
                    exchange_trust=31 if chosen_role == "创作者" else 42,
                    control=26 if chosen_role == "创作者" else 60,
                ),
                playable_roles=("平台", "创作者", "品牌方"),
            )

    inspection = inspect_material_seed(
        source_material="平台争议材料",
        llm_client=StructuredOverviewLLM(entity_count=3),
        entity_cap=8,
        selected_player_role="创作者",
    )

    selected_overview = inspection.role_overview_cards[0]
    comparison_overview = inspection.role_overview_cards[1]
    assert [card.role for card in inspection.role_overview_cards] == ["创作者", "平台", "品牌方"]
    assert selected_overview.is_selected is True
    assert selected_overview.is_baseline is True
    assert selected_overview.is_comparison is False
    assert selected_overview.metrics == {
        "control": inspection.viewpoints[0].metrics["control"],
        "pressure": inspection.viewpoints[0].metrics["pressure"],
        "credibility": inspection.viewpoints[0].metrics["credibility"],
        "narrative_control": inspection.viewpoints[0].metrics["narrative_control"],
    }
    assert selected_overview.relationship_summary == "当事创作者（创作者） ↔ 某平台（平台）"
    assert comparison_overview.role == inspection.comparison_role
    assert comparison_overview.is_comparison is True
    assert comparison_overview.contrast_score == inspection.viewpoints[1].contrast_score
    assert comparison_overview.focus_metrics == inspection.comparison_focus_metrics
    assert inspection.comparison_summary.startswith("平台：某平台（平台） ↔ 当事创作者（创作者）")
    assert "控制权" in inspection.comparison_summary


def test_inspect_material_seed_exposes_explicit_selected_and_comparison_cards() -> None:
    class ExplicitCardsLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            chosen_role = selected_player_role or "创作者"
            return ScenarioBlueprint(
                title="平台争议",
                premise="inspection 应把当前选择和主对比视角直接暴露为显式数据对象。",
                player_role=chosen_role,
                player_secret="不同角色持有不同证据片段。",
                objective="争取第一轮定义权。",
                opponent="主要对位角色",
                audience=("用户", "公众"),
                truth="上层 UI 不应再通过索引和标记自行回推关键卡片。",
                opening_event=WorldEvent(headline="舆论继续扩散", summary="多个阵营都在加码发声。", severity=76),
                entities=(
                    SeedEntity("platform", "某平台", "平台", "恢复秩序", "流程问题", 44, 86, "defensive", "机构主体"),
                    SeedEntity("creator", "当事创作者", "创作者", "保护个人叙事", "持续承压", 33, 82, "embattled", "主要直接冲突方"),
                    SeedEntity("brand", "合作品牌方", "品牌方", "控制风险敞口", "被视为共谋", 39, 72, "under fire", "次级冲突方"),
                ),
                initial_world=WorldState(
                    credibility=28 if chosen_role == "创作者" else 45,
                    treasury=44 if chosen_role == "创作者" else 57,
                    pressure=90 if chosen_role == "创作者" else 78,
                    price=45,
                    liquidity=39 if chosen_role == "创作者" else 52,
                    sell_pressure=66,
                    volatility=72,
                    community_panic=82 if chosen_role == "创作者" else 69,
                    rumor_level=76,
                    narrative_control=46 if chosen_role == "创作者" else 31,
                    exchange_trust=31 if chosen_role == "创作者" else 42,
                    control=26 if chosen_role == "创作者" else 60,
                ),
                playable_roles=("平台", "创作者", "品牌方"),
            )

    inspection = inspect_material_seed(
        source_material="平台争议材料",
        llm_client=ExplicitCardsLLM(entity_count=3),
        entity_cap=8,
        selected_player_role="创作者",
    )

    assert inspection.selected_viewpoint.role == "创作者"
    assert inspection.selected_viewpoint.is_selected is True
    assert inspection.comparison_viewpoint.role == inspection.comparison_role == "平台"
    assert inspection.selected_overview_card.role == "创作者"
    assert inspection.selected_overview_card.is_selected is True
    assert inspection.comparison_overview_card.role == inspection.comparison_role
    assert inspection.comparison_overview_card.is_comparison is True


def test_inspect_material_seed_exposes_selected_role_comparison_cards() -> None:
    class ComparisonCardsLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            chosen_role = selected_player_role or "创作者"
            metrics_by_role = {
                "创作者": {"control": 26, "pressure": 90, "credibility": 28, "narrative_control": 46},
                "平台": {"control": 60, "pressure": 78, "credibility": 45, "narrative_control": 31},
                "品牌方": {"control": 47, "pressure": 71, "credibility": 42, "narrative_control": 35},
            }
            metrics = metrics_by_role[chosen_role]
            return ScenarioBlueprint(
                title="平台争议",
                premise="inspection 应把当前视角对其他可选视角的对比暴露为稳定数据对象。",
                player_role=chosen_role,
                player_secret="不同角色持有不同证据片段。",
                objective="争取第一轮定义权。",
                opponent="主要对位角色",
                audience=("用户", "公众"),
                truth="多角色 seed 不应要求调用方自己重算对比差值。",
                opening_event=WorldEvent(headline="舆论继续扩散", summary="多个阵营都在加码发声。", severity=76),
                entities=(
                    SeedEntity("platform", "某平台", "平台", "恢复秩序", "流程问题", 44, 86, "defensive", "机构主体"),
                    SeedEntity("creator", "当事创作者", "创作者", "保护个人叙事", "持续承压", 33, 82, "embattled", "主要直接冲突方"),
                    SeedEntity("brand", "合作品牌方", "品牌方", "控制风险敞口", "被视为共谋", 39, 72, "under fire", "次级冲突方"),
                ),
                initial_world=WorldState(
                    credibility=metrics["credibility"],
                    treasury=44 if chosen_role == "创作者" else 57,
                    pressure=metrics["pressure"],
                    price=45,
                    liquidity=39 if chosen_role == "创作者" else 52,
                    sell_pressure=66,
                    volatility=72,
                    community_panic=82 if chosen_role == "创作者" else 69,
                    rumor_level=76,
                    narrative_control=metrics["narrative_control"],
                    exchange_trust=31 if chosen_role == "创作者" else 42,
                    control=metrics["control"],
                ),
                playable_roles=("平台", "创作者", "品牌方"),
            )

    inspection = inspect_material_seed(
        source_material="平台争议材料",
        llm_client=ComparisonCardsLLM(entity_count=3),
        entity_cap=8,
        selected_player_role="创作者",
    )

    assert [card.reference_role for card in inspection.selected_role_comparisons] == ["创作者", "创作者"]
    assert [card.compared_role for card in inspection.selected_role_comparisons] == ["平台", "品牌方"]
    primary = inspection.primary_selected_role_comparison
    assert primary is not None
    assert primary.compared_role == inspection.comparison_role == "平台"
    assert primary.is_primary is True
    assert primary.metric_deltas == inspection.comparison_viewpoint.metric_deltas
    assert primary.delta_summary == inspection.comparison_viewpoint.delta_summary
    assert primary.focus_metrics == inspection.comparison_focus_metrics
    assert primary.compared_relationship_summary == inspection.comparison_viewpoint.relationship_summary
    assert inspection.selected_role_comparisons[1].contrast_score < primary.contrast_score


def test_inspect_material_seed_selected_role_comparison_cards_include_reference_and_compared_snapshots() -> None:
    class ComparisonSnapshotLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            chosen_role = selected_player_role or "创作者"
            metrics_by_role = {
                "创作者": {"control": 26, "pressure": 90, "credibility": 28, "narrative_control": 46},
                "平台": {"control": 60, "pressure": 78, "credibility": 45, "narrative_control": 31},
                "品牌方": {"control": 47, "pressure": 71, "credibility": 42, "narrative_control": 35},
            }
            metrics = metrics_by_role[chosen_role]
            return ScenarioBlueprint(
                title="平台争议",
                premise="selected_role_comparisons 应同时携带参考视角和被比较视角的快照。",
                player_role=chosen_role,
                player_secret="不同角色持有不同证据片段。",
                objective="争取第一轮定义权。",
                opponent="主要对位角色",
                audience=("用户", "公众"),
                truth="上层 UI 需要无需回扫 viewpoint 列表即可拿到对比双方快照。",
                opening_event=WorldEvent(headline="舆论继续扩散", summary="多个阵营都在加码发声。", severity=76),
                entities=(
                    SeedEntity("platform", "某平台", "平台", "恢复秩序", "流程问题", 44, 86, "defensive", "机构主体"),
                    SeedEntity("creator", "当事创作者", "创作者", "保护个人叙事", "持续承压", 33, 82, "embattled", "主要直接冲突方"),
                    SeedEntity("brand", "合作品牌方", "品牌方", "控制风险敞口", "被视为共谋", 39, 72, "under fire", "次级冲突方"),
                ),
                initial_world=WorldState(
                    credibility=metrics["credibility"],
                    treasury=44 if chosen_role == "创作者" else 57,
                    pressure=metrics["pressure"],
                    price=45,
                    liquidity=39 if chosen_role == "创作者" else 52,
                    sell_pressure=66,
                    volatility=72,
                    community_panic=82 if chosen_role == "创作者" else 69,
                    rumor_level=76,
                    narrative_control=metrics["narrative_control"],
                    exchange_trust=31 if chosen_role == "创作者" else 42,
                    control=metrics["control"],
                ),
                playable_roles=("平台", "创作者", "品牌方"),
            )

    inspection = inspect_material_seed(
        source_material="平台争议材料",
        llm_client=ComparisonSnapshotLLM(entity_count=3),
        entity_cap=8,
        selected_player_role="创作者",
    )

    primary = inspection.primary_selected_role_comparison
    assert primary is not None
    assert primary.reference_role == "创作者"
    assert primary.reference_summary == inspection.selected_viewpoint.summary
    assert primary.reference_relationship_summary == inspection.selected_viewpoint.relationship_summary
    assert primary.reference_metrics == inspection.selected_viewpoint.metrics
    assert primary.compared_role == "平台"
    assert primary.compared_summary == inspection.comparison_viewpoint.summary
    assert primary.compared_metrics == inspection.comparison_viewpoint.metrics
    assert primary.compared_relationship_summary == inspection.comparison_viewpoint.relationship_summary


def test_inspect_material_seed_exposes_pairwise_role_comparison_cards() -> None:
    class PairwiseComparisonLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            chosen_role = selected_player_role or "创作者"
            metrics_by_role = {
                "创作者": {"control": 26, "pressure": 90, "credibility": 28, "narrative_control": 46},
                "平台": {"control": 60, "pressure": 78, "credibility": 45, "narrative_control": 31},
                "品牌方": {"control": 47, "pressure": 71, "credibility": 42, "narrative_control": 35},
            }
            metrics = metrics_by_role[chosen_role]
            return ScenarioBlueprint(
                title="平台争议",
                premise="inspection 应提供任意可选视角之间的稳定对比对象。",
                player_role=chosen_role,
                player_secret="不同角色持有不同证据片段。",
                objective="争取第一轮定义权。",
                opponent="主要对位角色",
                audience=("用户", "公众"),
                truth="调用方不应自己枚举所有 pair 再重算差值。",
                opening_event=WorldEvent(headline="舆论继续扩散", summary="多个阵营都在加码发声。", severity=76),
                entities=(
                    SeedEntity("platform", "某平台", "平台", "恢复秩序", "流程问题", 44, 86, "defensive", "机构主体"),
                    SeedEntity("creator", "当事创作者", "创作者", "保护个人叙事", "持续承压", 33, 82, "embattled", "主要直接冲突方"),
                    SeedEntity("brand", "合作品牌方", "品牌方", "控制风险敞口", "被视为共谋", 39, 72, "under fire", "次级冲突方"),
                ),
                initial_world=WorldState(
                    credibility=metrics["credibility"],
                    treasury=44 if chosen_role == "创作者" else 57,
                    pressure=metrics["pressure"],
                    price=45,
                    liquidity=39 if chosen_role == "创作者" else 52,
                    sell_pressure=66,
                    volatility=72,
                    community_panic=82 if chosen_role == "创作者" else 69,
                    rumor_level=76,
                    narrative_control=metrics["narrative_control"],
                    exchange_trust=31 if chosen_role == "创作者" else 42,
                    control=metrics["control"],
                ),
                playable_roles=("平台", "创作者", "品牌方"),
            )

    inspection = inspect_material_seed(
        source_material="平台争议材料",
        llm_client=PairwiseComparisonLLM(entity_count=3),
        entity_cap=8,
        selected_player_role="创作者",
    )

    assert [(card.reference_role, card.compared_role) for card in inspection.pairwise_role_comparisons] == [
        ("创作者", "平台"),
        ("创作者", "品牌方"),
        ("平台", "品牌方"),
    ]
    platform_vs_brand = inspection.pairwise_role_comparisons[2]
    platform_card = next(card for card in inspection.viewpoints if card.role == "平台")
    brand_card = next(card for card in inspection.viewpoints if card.role == "品牌方")
    expected_deltas = {
        key: brand_card.metrics[key] - platform_card.metrics[key]
        for key in ("control", "pressure", "credibility", "narrative_control")
    }
    assert platform_vs_brand.reference_role == "平台"
    assert platform_vs_brand.compared_role == "品牌方"
    assert platform_vs_brand.reference_summary == platform_card.summary
    assert platform_vs_brand.compared_summary == brand_card.summary
    assert platform_vs_brand.metric_deltas == expected_deltas
    assert platform_vs_brand.contrast_score == sum(abs(value) for value in expected_deltas.values())
    assert all(metric in expected_deltas for metric in platform_vs_brand.focus_metrics)


def test_inspect_material_seed_resolves_primary_counterpart_even_when_viewpoint_entity_is_missing() -> None:
    class MissingViewpointEntityLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            chosen_role = selected_player_role or "州政府"
            return ScenarioBlueprint(
                title="港航责任风暴",
                premise="可选视角里有一个角色没有被实体列表精确展开。",
                player_role=chosen_role,
                player_secret="航运集团内部已准备甩锅方案。",
                objective="先守住自己的解释权。",
                opponent="主要对位角色",
                audience=("公众", "物流客户", "监管部门"),
                truth="实体抽取不完整时，inspection 仍应保留多视角对位信息。",
                opening_event=WorldEvent(headline="复航方案受阻", summary="多方在责任和时间表上相互卡位。", severity=82),
                entities=(
                    SeedEntity("gov", "州政府与地方应急体系", "州政府应急体系", "压住整体风险", "处置迟缓", 48, 88, "defensive", "制度性协调方"),
                    SeedEntity("port", "港口运营链", "港口运营体系", "尽快恢复主航道", "工程窗口期缩短", 41, 83, "defensive", "现场协调方"),
                    SeedEntity("public", "沿海物流客户", "客户群体", "确认损失边界", "供应链继续延误", 34, 58, "watching", "外围压力源"),
                ),
                initial_world=WorldState(
                    credibility=46,
                    treasury=55,
                    pressure=82,
                    price=44,
                    liquidity=49,
                    sell_pressure=64,
                    volatility=70,
                    community_panic=72,
                    rumor_level=73,
                    narrative_control=34,
                    exchange_trust=43,
                    control=48,
                ),
                playable_roles=("州政府", "港口", "航运集团"),
            )

    inspection = inspect_material_seed(
        source_material="港航风暴材料",
        llm_client=MissingViewpointEntityLLM(entity_count=3),
        entity_cap=8,
        selected_player_role="州政府",
    )

    shipping_card = next(card for card in inspection.viewpoints if card.role == "航运集团")
    assert shipping_card.player_entity == "航运集团"
    assert shipping_card.player_entity_role == "航运集团"
    assert shipping_card.primary_counterpart == "州政府与地方应急体系"
    assert shipping_card.primary_counterpart_role == "州政府应急体系"
    assert shipping_card.primary_counterpart_resolved is True
    shipping_overview = next(card for card in inspection.role_overview_cards if card.role == "航运集团")
    assert shipping_overview.primary_counterpart == "州政府与地方应急体系"
    assert shipping_overview.primary_counterpart_resolved is True


def test_build_scenario_without_direct_player_entity_still_calibrates_viewpoint_specific_world() -> None:
    class MissingPlayerEntityCalibrationLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            chosen_role = selected_player_role or "州政府"
            return ScenarioBlueprint(
                title="港航责任风暴",
                premise="即使实体抽取遗漏了某个可选视角，开局也必须保持视角差异。",
                player_role=chosen_role,
                player_secret="真正的责任边界仍未完全公开。",
                objective="守住第一轮解释权。",
                opponent="主要对位角色",
                audience=("公众", "物流客户", "监管部门"),
                truth="视角缺失不该让多角色 seed 退化成同一个开局。",
                opening_event=WorldEvent(headline="复航方案受阻", summary="多方围绕责任和恢复节奏互相卡位。", severity=82),
                entities=(
                    SeedEntity("gov", "州政府与地方应急体系", "州政府应急体系", "压住整体风险", "处置迟缓", 48, 88, "defensive", "制度性协调方"),
                    SeedEntity("port", "港口运营链", "港口运营体系", "尽快恢复主航道", "工程窗口期缩短", 41, 83, "defensive", "现场协调方"),
                    SeedEntity("public", "沿海物流客户", "客户群体", "确认损失边界", "供应链继续延误", 34, 58, "watching", "外围压力源"),
                ),
                initial_world=WorldState(
                    credibility=46,
                    treasury=55,
                    pressure=82,
                    price=44,
                    liquidity=49,
                    sell_pressure=64,
                    volatility=70,
                    community_panic=72,
                    rumor_level=73,
                    narrative_control=34,
                    exchange_trust=43,
                    control=48,
                ),
                playable_roles=("州政府", "港口", "航运集团"),
            )

    llm = MissingPlayerEntityCalibrationLLM(entity_count=3)
    government = build_scenario_from_material(
        source_material="港航风暴材料",
        llm_client=llm,
        entity_cap=8,
        selected_player_role="州政府",
    )
    shipping = build_scenario_from_material(
        source_material="港航风暴材料",
        llm_client=llm,
        entity_cap=8,
        selected_player_role="航运集团",
    )

    differing_metrics = [
        key
        for key in ("control", "credibility", "pressure", "community_panic", "narrative_control")
        if getattr(government.initial_world, key) != getattr(shipping.initial_world, key)
    ]
    assert len(differing_metrics) >= 3
    assert government.initial_world.control > shipping.initial_world.control
    assert shipping.initial_world.pressure > government.initial_world.pressure


def test_build_scenario_without_direct_player_entity_still_diverges_when_raw_initial_world_is_identical() -> None:
    class MissingPlayerEntitySameWorldLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            chosen_role = selected_player_role or "甲方团队"
            return ScenarioBlueprint(
                title="双边责任风暴",
                premise="即使所有视角先返回同一个 raw world，系统也必须根据选定视角做差异化校准。",
                player_role=chosen_role,
                player_secret="真正责任边界仍未完全公开。",
                objective="守住第一轮解释权。",
                opponent="主要对位角色",
                audience=("公众", "物流客户", "监管部门"),
                truth="缺少直连玩家实体时，不能退化成完全同一个开局。",
                opening_event=WorldEvent(headline="联调方案受阻", summary="两边团队围绕责任和恢复节奏互相卡位。", severity=82),
                entities=(
                    SeedEntity("ops", "协调专班", "处置协调体系", "压住整体风险", "处置迟缓", 48, 88, "defensive", "制度性协调方"),
                    SeedEntity("vendor", "外包执行链", "执行承包链", "尽快恢复节点", "工程窗口期缩短", 41, 83, "defensive", "现场执行方"),
                    SeedEntity("public", "沿海物流客户", "客户群体", "确认损失边界", "供应链继续延误", 34, 58, "watching", "外围压力源"),
                ),
                initial_world=WorldState(
                    credibility=46,
                    treasury=55,
                    pressure=82,
                    price=44,
                    liquidity=49,
                    sell_pressure=64,
                    volatility=70,
                    community_panic=72,
                    rumor_level=73,
                    narrative_control=34,
                    exchange_trust=43,
                    control=48,
                ),
                playable_roles=("甲方团队", "乙方团队"),
            )

    llm = MissingPlayerEntitySameWorldLLM(entity_count=3)
    government = build_scenario_from_material(
        source_material="双边风暴材料",
        llm_client=llm,
        entity_cap=8,
        selected_player_role="甲方团队",
    )
    shipping = build_scenario_from_material(
        source_material="双边风暴材料",
        llm_client=llm,
        entity_cap=8,
        selected_player_role="乙方团队",
    )

    differing_metrics = [
        key
        for key in ("control", "credibility", "pressure", "community_panic", "narrative_control")
        if getattr(government.initial_world, key) != getattr(shipping.initial_world, key)
    ]
    assert len(differing_metrics) >= 3
    assert government.initial_world.control > shipping.initial_world.control
    assert shipping.initial_world.pressure > government.initial_world.pressure


def test_inspect_material_seed_marks_unresolved_player_entity_fallback_in_cards() -> None:
    class MissingViewpointEntityLLM(FakeWorldgenLLM):
        def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
            chosen_role = selected_player_role or "州政府"
            return ScenarioBlueprint(
                title="港航责任风暴",
                premise="inspection 应该告诉上层这个视角的玩家实体是 fallback。",
                player_role=chosen_role,
                player_secret="航运集团内部已准备甩锅方案。",
                objective="先守住自己的解释权。",
                opponent="主要对位角色",
                audience=("公众", "物流客户", "监管部门"),
                truth="实体抽取不完整时，inspection 仍应暴露解析状态。",
                opening_event=WorldEvent(headline="复航方案受阻", summary="多方在责任和时间表上相互卡位。", severity=82),
                entities=(
                    SeedEntity("gov", "州政府与地方应急体系", "州政府应急体系", "压住整体风险", "处置迟缓", 48, 88, "defensive", "制度性协调方"),
                    SeedEntity("port", "港口运营链", "港口运营体系", "尽快恢复主航道", "工程窗口期缩短", 41, 83, "defensive", "现场协调方"),
                    SeedEntity("public", "沿海物流客户", "客户群体", "确认损失边界", "供应链继续延误", 34, 58, "watching", "外围压力源"),
                ),
                initial_world=WorldState(
                    credibility=46,
                    treasury=55,
                    pressure=82,
                    price=44,
                    liquidity=49,
                    sell_pressure=64,
                    volatility=70,
                    community_panic=72,
                    rumor_level=73,
                    narrative_control=34,
                    exchange_trust=43,
                    control=48,
                ),
                playable_roles=("州政府", "港口", "航运集团"),
            )

    inspection = inspect_material_seed(
        source_material="港航风暴材料",
        llm_client=MissingViewpointEntityLLM(entity_count=3),
        entity_cap=8,
        selected_player_role="州政府",
    )

    shipping_card = next(card for card in inspection.viewpoints if card.role == "航运集团")
    assert shipping_card.player_entity == "航运集团"
    assert shipping_card.player_entity_role == "航运集团"
    assert shipping_card.player_entity_resolved is False
    shipping_overview = next(card for card in inspection.role_overview_cards if card.role == "航运集团")
    assert shipping_overview.player_entity_resolved is False
