import os
import subprocess
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

from eventforge.__main__ import print_intro, print_role_inspection
from eventforge.domain import MaterialSeedInspection, ScenarioRoleComparisonCard, ScenarioRoleOverviewCard, ScenarioViewpointCard, WorldEvent, WorldState

ROOT = Path(__file__).resolve().parents[1]



def test_module_launcher_requires_llm_configuration() -> None:
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    env.pop("OPENAI_BASE_URL", None)
    env.pop("OPENAI_MODEL", None)
    result = subprocess.run(
        [sys.executable, "-m", "eventforge", "--mode", "auto", "--turns", "1"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "OPENAI_API_KEY" in result.stderr or "OPENAI_API_KEY" in result.stdout


def test_module_launcher_accepts_player_role_flag() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "eventforge", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=dict(os.environ),
    )

    assert result.returncode == 0
    assert "--player-role" in result.stdout
    assert "--list-player-roles" in result.stdout



def test_print_intro_uses_frozen_world_metadata_over_legacy_scenario_wrapper() -> None:
    game = SimpleNamespace(
        scenario=SimpleNamespace(
            title="Legacy Demo Title",
            premise="旧前提",
            player_role="legacy-role",
            objective="legacy objective",
            opponent="legacy opponent",
            player_secret="legacy secret",
            playable_roles=("legacy-role",),
            opening_event=WorldEvent(headline="旧开局", summary="旧摘要", severity=30),
        ),
        frozen_world=SimpleNamespace(
            title="Frozen Crisis",
            premise="冻结世界前提",
            player_role="校方",
            objective="根据冻结世界推进局势",
            opponent="冻结世界对位",
            player_secret="冻结世界中的关键事实。",
            selectable_roles=("校方", "杨景媛"),
            opening_event=WorldEvent(headline="冻结开局", summary="冻结摘要", severity=80),
        ),
        state=WorldState(control=77, pressure=19, credibility=73, narrative_control=64),
        agent_profiles=(SimpleNamespace(name="Frozen Observer", role="observer", stance="等待冻结世界的信号", trust_in_player=61),),
    )

    buffer = StringIO()
    with redirect_stdout(buffer):
        print_intro(game)

    output = buffer.getvalue()

    assert "Frozen Crisis" in output
    assert "你扮演：校方" in output
    assert "意图：根据冻结世界推进局势" in output
    assert "真相：冻结世界中的关键事实。" in output
    assert "可选视角：校方 / 杨景媛" in output
    assert "开局事件：冻结开局" in output
    assert "Legacy Demo Title" not in output


def test_module_launcher_lists_roles_from_material() -> None:
    material = ROOT / "tmp-test-material.md"
    material.write_text("test material", encoding="utf-8")
    env = dict(os.environ)
    env.update(
        {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_BASE_URL": "https://example.invalid/v1",
            "OPENAI_MODEL": "test-model",
            "PYTHONPATH": str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", ""),
        }
    )
    env["EVENTFORGE_TEST_STUB_BLUEPRINT"] = "1"
    try:
        result = subprocess.run(
            [sys.executable, "-m", "eventforge", "--material-file", str(material), "--list-player-roles"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=env,
        )
    finally:
        material.unlink(missing_ok=True)

    assert result.returncode == 0
    assert "# 可选玩家角色" in result.stdout
    assert "- 校方" in result.stdout
    assert "- 杨景媛" in result.stdout
    assert "控制权" in result.stdout
    assert "压力" in result.stdout
    assert "当前选择：校方" in result.stdout
    assert "基准视角：校方" in result.stdout
    assert "主对比视角：杨景媛" in result.stdout
    assert "基准剖面：控制权" in result.stdout
    assert "当前视角摘要：校方：武汉大学校方（校方） ↔ 杨景媛（杨景媛）" in result.stdout
    assert "主对比摘要：杨景媛：杨景媛（杨景媛） ↔ 武汉大学校方（校方）" in result.stdout
    assert "视角速览：" in result.stdout
    assert "- 校方：武汉大学校方（校方） ↔ 杨景媛（杨景媛）" in result.stdout
    assert "视角矩阵：" in result.stdout
    assert "- [selected][baseline] 校方 | 控制权" in result.stdout
    assert "- [comparison] 杨景媛 | 控制权" in result.stdout
    assert "视角对比：" in result.stdout
    assert "- [primary] 校方 → 杨景媛 | 当前 控制权" in result.stdout
    assert "| 对比 控制权" in result.stdout
    assert "- 校方 [selected][baseline]" in result.stdout
    assert "关系：武汉大学校方（校方） ↔ 杨景媛（杨景媛）" in result.stdout
    assert "相对基准：控制权" in result.stdout
    assert "差异强度：" in result.stdout
    assert "差异焦点：" in result.stdout
    assert "玩家实体：武汉大学校方（校方）" in result.stdout
    assert "主要对位：杨景媛（杨景媛）" in result.stdout


def test_print_role_inspection_marks_fallback_player_entity_resolution(capsys) -> None:
    inspection = MaterialSeedInspection(
        title="港航责任风暴",
        playable_roles=("州政府", "航运集团"),
        selected_role="州政府",
        baseline_role="州政府",
        baseline_summary="控制权 52 / 压力 80 / 公信力 48 / 叙事控制 34",
        viewpoints=(
            ScenarioViewpointCard(
                role="州政府",
                summary="控制权 52 / 压力 80 / 公信力 48 / 叙事控制 34",
                metrics={"control": 52, "pressure": 80, "credibility": 48, "narrative_control": 34},
                metric_deltas={"control": 0, "pressure": 0, "credibility": 0, "narrative_control": 0},
                delta_summary="无显著差异",
                contrast_score=0,
                focus_metrics=(),
                key_entities=("州政府与地方应急体系", "港口运营链"),
                player_entity="州政府与地方应急体系",
                player_entity_role="州政府应急体系",
                player_entity_resolved=True,
                primary_counterpart="港口运营链",
                primary_counterpart_role="港口运营体系",
                relationship_summary="州政府与地方应急体系（州政府应急体系） ↔ 港口运营链（港口运营体系）",
                opening_headline="复航方案受阻",
                is_selected=True,
                is_baseline=True,
            ),
            ScenarioViewpointCard(
                role="航运集团",
                summary="控制权 34 / 压力 88 / 公信力 36 / 叙事控制 41",
                metrics={"control": 34, "pressure": 88, "credibility": 36, "narrative_control": 41},
                metric_deltas={"control": -18, "pressure": 8, "credibility": -12, "narrative_control": 7},
                delta_summary="控制权 -18 / 公信力 -12 / 压力 +8",
                contrast_score=45,
                focus_metrics=("control", "credibility", "pressure"),
                key_entities=("州政府与地方应急体系", "港口运营链"),
                player_entity="航运集团",
                player_entity_role="航运集团",
                player_entity_resolved=False,
                primary_counterpart="州政府与地方应急体系",
                primary_counterpart_role="州政府应急体系",
                relationship_summary="航运集团（航运集团） ↔ 州政府与地方应急体系（州政府应急体系）",
                opening_headline="复航方案受阻",
                is_selected=False,
                is_baseline=False,
            ),
        ),
        role_overview_cards=(
            ScenarioRoleOverviewCard(
                role="州政府",
                metrics={"control": 52, "pressure": 80, "credibility": 48, "narrative_control": 34},
                summary="控制权 52 / 压力 80 / 公信力 48 / 叙事控制 34",
                relationship_summary="州政府与地方应急体系（州政府应急体系） ↔ 港口运营链（港口运营体系）",
                delta_summary="无显著差异",
                contrast_score=0,
                focus_metrics=(),
                primary_counterpart="港口运营链",
                primary_counterpart_role="港口运营体系",
                player_entity_resolved=True,
                is_selected=True,
                is_baseline=True,
            ),
            ScenarioRoleOverviewCard(
                role="航运集团",
                metrics={"control": 34, "pressure": 88, "credibility": 36, "narrative_control": 41},
                summary="控制权 34 / 压力 88 / 公信力 36 / 叙事控制 41",
                relationship_summary="航运集团（航运集团） ↔ 州政府与地方应急体系（州政府应急体系）",
                delta_summary="控制权 -18 / 公信力 -12 / 压力 +8",
                contrast_score=45,
                focus_metrics=("control", "credibility", "pressure"),
                primary_counterpart="州政府与地方应急体系",
                primary_counterpart_role="州政府应急体系",
                player_entity_resolved=False,
                is_comparison=True,
            ),
        ),
        comparison_role="航运集团",
        comparison_focus="控制权 -18 / 公信力 -12 / 压力 +8",
        comparison_focus_metrics=("control", "credibility", "pressure"),
        comparison_focus_count=3,
    )

    print_role_inspection(inspection)
    output = capsys.readouterr().out

    assert "玩家实体：州政府与地方应急体系（州政府应急体系）" in output
    assert "玩家实体：航运集团（航运集团） [fallback]" in output


def test_print_role_inspection_outputs_pairwise_role_comparisons(capsys) -> None:
    inspection = MaterialSeedInspection(
        title="平台争议",
        playable_roles=("创作者", "平台", "品牌方"),
        selected_role="创作者",
        baseline_role="创作者",
        baseline_summary="控制权 26 / 压力 90 / 公信力 28 / 叙事控制 46",
        pairwise_role_comparisons=(
            ScenarioRoleComparisonCard(
                reference_role="创作者",
                reference_summary="控制权 26 / 压力 90 / 公信力 28 / 叙事控制 46",
                reference_metrics={"control": 26, "pressure": 90, "credibility": 28, "narrative_control": 46},
                reference_relationship_summary="当事创作者（创作者） ↔ 某平台（平台）",
                compared_role="平台",
                compared_summary="控制权 60 / 压力 78 / 公信力 45 / 叙事控制 31",
                compared_metrics={"control": 60, "pressure": 78, "credibility": 45, "narrative_control": 31},
                metric_deltas={"control": 34, "pressure": -12, "credibility": 17, "narrative_control": -15},
                delta_summary="控制权 +34 / 公信力 +17 / 叙事控制 -15",
                contrast_score=78,
                focus_metrics=("control", "credibility", "narrative_control"),
                compared_relationship_summary="某平台（平台） ↔ 当事创作者（创作者）",
                is_primary=True,
            ),
            ScenarioRoleComparisonCard(
                reference_role="平台",
                reference_summary="控制权 60 / 压力 78 / 公信力 45 / 叙事控制 31",
                reference_metrics={"control": 60, "pressure": 78, "credibility": 45, "narrative_control": 31},
                reference_relationship_summary="某平台（平台） ↔ 当事创作者（创作者）",
                compared_role="品牌方",
                compared_summary="控制权 47 / 压力 71 / 公信力 42 / 叙事控制 35",
                compared_metrics={"control": 47, "pressure": 71, "credibility": 42, "narrative_control": 35},
                metric_deltas={"control": -13, "pressure": -7, "credibility": -3, "narrative_control": 4},
                delta_summary="控制权 -13 / 压力 -7 / 叙事控制 +4",
                contrast_score=27,
                focus_metrics=("control", "pressure", "narrative_control"),
                compared_relationship_summary="合作品牌方（品牌方） ↔ 某平台（平台）",
                is_primary=False,
            ),
        ),
    )

    print_role_inspection(inspection)
    output = capsys.readouterr().out

    assert "任意视角对照：" in output
    assert "- [primary] 创作者 → 平台 | 当前 控制权 26 / 压力 90 / 公信力 28 / 叙事控制 46 | 对比 控制权 60 / 压力 78 / 公信力 45 / 叙事控制 31" in output
    assert "- 平台 → 品牌方 | 当前 控制权 60 / 压力 78 / 公信力 45 / 叙事控制 31 | 对比 控制权 47 / 压力 71 / 公信力 42 / 叙事控制 35 | 控制权 -13 / 压力 -7 / 叙事控制 +4" in output
