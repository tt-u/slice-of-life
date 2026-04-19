import json
from pathlib import Path

from eventforge.domain import (
    EntityResearchCard,
    EvidenceNote,
    MaterialResearchPack,
    ResearchDispute,
    ResearchRelationship,
)
from eventforge.research import build_wuhan_university_yang_jingyuan_research_pack


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