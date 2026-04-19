import json
from pathlib import Path

from eventforge.domain import (
    EntityResearchCard,
    EvidenceNote,
    FrozenInitialWorld,
    MaterialResearchPack,
    ResearchDispute,
    ResearchRelationship,
)
from eventforge.research import (
    build_wuhan_university_yang_jingyuan_frozen_world,
    build_wuhan_university_yang_jingyuan_research_pack,
)


ROOT = Path(__file__).resolve().parents[1]


def test_material_research_pack_round_trips_with_entity_cards_and_disputes() -> None:
    pack = MaterialResearchPack(
        case_id="wuhan-university-yang-jingyuan",
        title="武汉大学杨景媛事件",
        source_material="基于公开通报与判决节点整理。",
        premise="校方处置、司法判决与论文争议彼此牵动。",
        opponent="对位阵营与持续扩散的舆论压力",
        audience=("学生", "校友", "公众"),
        truth="公开争议同时牵动纪律处分、学位复核与网络传言清理。",
        entities=(),
        candidate_viewpoints=("校方", "杨景媛"),
        opening_event=build_wuhan_university_yang_jingyuan_research_pack().opening_event,
        research_notes=("保留直接冲突双方",),
        entity_cards=(
            EntityResearchCard(
                entity_id="whu-admin",
                name="武汉大学校方",
                role="校方",
                stance="强调依法依规复核并试图止损",
                public_position="尊重司法判决、维持杨景媛学位、撤销肖某瑫处分。",
                conflict_stakes="既要回应程序公信力，也要压住持续外溢的舆情冲击。",
                notable_pressures=("公信力受损", "多线问责压力"),
                relationships=(
                    ResearchRelationship(
                        target_entity_id="yang-jingyuan",
                        relation_type="institutional-review",
                        summary="对其论文和学位授予流程进行了二次复核。",
                    ),
                ),
                evidence=(
                    EvidenceNote(
                        source_title="武汉大学情况通报",
                        source_url="https://www.whu.edu.cn/info/5231/258444.htm",
                        note="校方通报了处分撤销、学位维持和问责安排。",
                    ),
                ),
            ),
        ),
        disputed_points=(
            ResearchDispute(
                key="discipline-reversal",
                claim="是否应撤销对肖某瑫的纪律处分",
                sides=("校方/司法节点", "质疑校方程序的人群"),
                status="contested",
            ),
        ),
    )

    payload = pack.to_payload()

    assert payload["entity_cards"][0]["entity_id"] == "whu-admin"
    assert payload["entity_cards"][0]["relationships"][0]["relation_type"] == "institutional-review"
    assert payload["disputed_points"][0]["key"] == "discipline-reversal"

    restored = MaterialResearchPack.from_payload(payload)

    assert restored == pack


def test_wuhan_anchor_research_pack_captures_direct_conflict_parties_and_evidence() -> None:
    pack = build_wuhan_university_yang_jingyuan_research_pack()

    assert pack.case_id == "wuhan-university-yang-jingyuan"
    assert pack.candidate_viewpoints == ("校方", "杨景媛")
    assert len(pack.entity_cards) >= 4
    assert {card.role for card in pack.entity_cards} >= {"校方", "杨景媛"}
    assert any(dispute.key == "degree-integrity" for dispute in pack.disputed_points)
    assert any(
        note.source_url == "https://www.whu.edu.cn/info/5231/258444.htm"
        for card in pack.entity_cards
        for note in card.evidence
    )


def test_wuhan_anchor_research_pack_fixture_matches_serialized_payload() -> None:
    pack = build_wuhan_university_yang_jingyuan_research_pack()
    fixture_path = ROOT / "examples" / "research" / "wuhan-university-yang-jingyuan.json"

    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    restored = MaterialResearchPack.from_payload(payload)

    assert restored == pack


def test_wuhan_anchor_frozen_world_builds_world_owned_contract_for_school_role() -> None:
    frozen = build_wuhan_university_yang_jingyuan_frozen_world(player_role="校方")

    assert isinstance(frozen, FrozenInitialWorld)
    assert frozen.world_id == "wuhan-university-yang-jingyuan-school"
    assert frozen.title == "武汉大学杨景媛事件"
    assert frozen.player_role == "校方"
    assert frozen.selectable_roles == ("校方", "杨景媛")
    assert frozen.allowed_turn_counts == (4, 6, 8, 10)
    assert frozen.action_grammar is not None
    assert frozen.action_grammar.menu_size == 4
    assert len(frozen.action_grammar.rules) == 4
    assert all(rule.minimum_upside_count >= 1 for rule in frozen.action_grammar.rules)
    assert all(rule.minimum_downside_count >= 1 for rule in frozen.action_grammar.rules)
    assert [band.label for band in frozen.ending_bands] == ["程序定锚", "争议拖行", "问责失序", "信任坠空"]
    assert frozen.resolve_ending_band(82).label == "程序定锚"
    assert frozen.resolve_ending_band(55).label == "争议拖行"


def test_wuhan_anchor_frozen_world_materially_differs_between_school_and_yang_roles() -> None:
    school_world = build_wuhan_university_yang_jingyuan_frozen_world(player_role="校方")
    yang_world = build_wuhan_university_yang_jingyuan_frozen_world(player_role="杨景媛")

    school_dimensions = school_world.initial_dimension_map()
    yang_dimensions = yang_world.initial_dimension_map()

    assert school_world.player_role == "校方"
    assert yang_world.player_role == "杨景媛"
    assert school_world.world_id != yang_world.world_id
    assert school_world.objective != yang_world.objective
    assert school_dimensions["control"] >= yang_dimensions["control"] + 20
    assert yang_dimensions["pressure"] >= school_dimensions["pressure"] + 15
    assert yang_dimensions["narrative_control"] >= school_dimensions["narrative_control"] + 10
    assert school_dimensions["credibility"] >= yang_dimensions["credibility"] + 8


def test_wuhan_anchor_frozen_world_fixture_matches_serialized_payloads_for_each_role() -> None:
    for player_role, fixture_name in (("校方", "wuhan-university-yang-jingyuan-school.json"), ("杨景媛", "wuhan-university-yang-jingyuan-yang-jingyuan.json")):
        frozen = build_wuhan_university_yang_jingyuan_frozen_world(player_role=player_role)
        fixture_path = ROOT / "examples" / "worlds" / fixture_name

        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        restored = FrozenInitialWorld.from_payload(payload)

        assert restored == frozen
