from __future__ import annotations

import argparse
import sys
from pathlib import Path

from eventforge.domain import ActionCard, TurnChoice, WorldReport
from eventforge.engine import build_game
from eventforge.llm import OpenAICompatibleLLM
from eventforge.worldgen import build_scenario_from_material, inspect_material_seed


def main() -> None:
    parser = argparse.ArgumentParser(description="Play the Flash Crash Demo")
    parser.add_argument("--mode", choices=("interactive", "auto"), default="interactive")
    parser.add_argument("--turns", type=int, default=6)
    parser.add_argument("--material-file", type=str, default=None)
    parser.add_argument("--player-role", type=str, default=None)
    parser.add_argument("--list-player-roles", action="store_true")
    args = parser.parse_args()

    try:
        if args.material_file:
            material_path = Path(args.material_file)
            source_material = material_path.read_text(encoding="utf-8")
            llm_client = OpenAICompatibleLLM()
            if args.list_player_roles:
                inspection = inspect_material_seed(
                    source_material=source_material,
                    llm_client=llm_client,
                    selected_player_role=args.player_role,
                )
                print_role_inspection(inspection)
                return
            scenario = build_scenario_from_material(
                source_material=source_material,
                llm_client=llm_client,
                selected_player_role=args.player_role,
            )
            game = build_game(turns=args.turns, llm_client=llm_client, scenario=scenario)
        else:
            game = build_game(turns=args.turns)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)

    print_intro(game)

    while game.state.turn_index < game.state.turns_total:
        pre_turn_event = game.begin_turn()
        print_turn_header(game, pre_turn_event)
        actions = game.available_actions()
        if args.mode == "interactive":
            choice = prompt_for_choice(actions)
        else:
            choice = game.auto_choose_action()
            print(f"[AUTO] {choice.action.label}")
        resolution = game.apply_choice(choice)
        print_resolution(resolution)

    print_final(game.build_world_report())


def print_intro(game) -> None:
    scenario = game.scenario
    print(f"# {scenario.title}")
    print()
    print(scenario.premise)
    print()
    print(f"你扮演：{scenario.player_role}")
    print(f"意图：{scenario.objective}")
    print(f"对手：{scenario.opponent}")
    print(f"真相：{scenario.player_secret}")
    if scenario.playable_roles:
        print(f"可选视角：{' / '.join(scenario.playable_roles)}")
    print()
    print(f"开局事件：{scenario.opening_event.headline}")
    print(scenario.opening_event.summary)
    print("开局剖面：" + summarize_initial_world(game.state))
    print()
    print("关键角色：")
    for profile in game.agent_profiles:
        print(f"- {profile.name} ({profile.role})：{profile.stance} / 信任 {profile.trust_in_player}")
    print()


def print_role_inspection(inspection) -> None:
    print(f"# 可选玩家角色：{inspection.title}")
    print(f"当前选择：{inspection.selected_role or inspection.baseline_role}")
    print(f"基准视角：{inspection.baseline_role}")
    if inspection.comparison_role:
        print(f"主对比视角：{inspection.comparison_role}")
    print(f"基准剖面：{inspection.baseline_summary}")
    if inspection.selected_summary:
        print(f"当前视角摘要：{inspection.selected_summary}")
    if inspection.comparison_summary:
        print(f"主对比摘要：{inspection.comparison_summary}")
    print(f"差异焦点：{inspection.comparison_focus}")
    if inspection.role_overview:
        print("视角速览：")
        for line in inspection.role_overview:
            print(f"- {line}")
    if inspection.role_overview_cards:
        print("视角矩阵：")
        for card in inspection.role_overview_cards:
            print(f"- {format_role_overview_matrix_line(card)}")
    if inspection.selected_role_comparisons:
        print("视角对比：")
        for card in inspection.selected_role_comparisons:
            print(f"- {format_selected_role_comparison_line(card)}")
    if inspection.pairwise_role_comparisons:
        print("任意视角对照：")
        for card in inspection.pairwise_role_comparisons:
            print(f"- {format_selected_role_comparison_line(card)}")
    for card in inspection.viewpoints:
        tags = []
        if card.is_selected:
            tags.append("selected")
        if card.is_baseline:
            tags.append("baseline")
        suffix = "".join(f"[{tag}]" for tag in tags)
        print(f"- {card.role}{(' ' + suffix) if suffix else ''}")
        print(f"  开局事件：{card.opening_headline}")
        print(f"  开局剖面：{card.summary}")
        print(f"  关系：{card.relationship_summary}")
        print(
            "  相对基准："
            f"控制权 {card.metric_deltas['control']:+d} / 压力 {card.metric_deltas['pressure']:+d} / "
            f"公信力 {card.metric_deltas['credibility']:+d} / 叙事控制 {card.metric_deltas['narrative_control']:+d}"
        )
        print(f"  差异强度：{card.contrast_score}")
        print(f"  差异焦点：{card.delta_summary}")
        player_suffix = " [fallback]" if not card.player_entity_resolved else ""
        print(f"  玩家实体：{card.player_entity}（{card.player_entity_role}）{player_suffix}")
        print(f"  主要对位：{card.primary_counterpart}（{card.primary_counterpart_role}）")
        print(f"  关键实体：{' / '.join(card.key_entities)}")


def format_role_overview_matrix_line(card) -> str:
    tags = []
    if card.is_selected:
        tags.append("selected")
    if card.is_baseline:
        tags.append("baseline")
    if card.is_comparison:
        tags.append("comparison")
    prefix = "".join(f"[{tag}]" for tag in tags)
    metrics = (
        f"控制权 {card.metrics['control']} / 压力 {card.metrics['pressure']} / "
        f"公信力 {card.metrics['credibility']} / 叙事控制 {card.metrics['narrative_control']}"
    )
    focus = "基准视角" if card.contrast_score == 0 else card.delta_summary
    return f"{prefix + ' ' if prefix else ''}{card.role} | {metrics} | {focus} | {card.relationship_summary}"


def format_selected_role_comparison_line(card) -> str:
    prefix = "[primary] " if card.is_primary else ""
    summary = card.delta_summary or "无显著差异"
    return (
        f"{prefix}{card.reference_role} → {card.compared_role} | "
        f"当前 {card.reference_summary} | 对比 {card.compared_summary} | {summary} | "
        f"{card.compared_relationship_summary}"
    )


def summarize_initial_world(state) -> str:
    return (
        f"控制权 {state.control} / 压力 {state.pressure} / 公信力 {state.credibility} / "
        f"叙事控制 {state.narrative_control}"
    )


def summarize_focus_metrics(card) -> str:
    labels = {
        "control": "控制权",
        "pressure": "压力",
        "credibility": "公信力",
        "narrative_control": "叙事控制",
    }
    if not card.focus_metrics:
        return "无显著差异"
    return " / ".join(f"{labels.get(metric, metric)} {card.metric_deltas[metric]:+d}" for metric in card.focus_metrics)


def print_turn_header(game, pre_turn_event) -> None:
    state = game.state
    print(f"\n## 回合 {state.turn_index + 1}/{state.turns_total}")
    print(f"回合前事件：{pre_turn_event.actor_name} / {pre_turn_event.headline}")
    print(pre_turn_event.summary)
    print(
        f"控制权 {state.control} | 叙事控制 {state.narrative_control} | 社区恐慌 {state.community_panic} | "
        f"交易所信任 {state.exchange_trust} | 币价 {state.price} | 国库 {state.treasury}"
    )


def prompt_for_choice(actions: tuple[ActionCard, ...]) -> TurnChoice:
    for index, action in enumerate(actions, start=1):
        print(f"{index}. {action.label} — {action.description}")
    while True:
        raw = input("选择行动编号：").strip()
        if not raw.isdigit():
            print("请输入数字。")
            continue
        idx = int(raw)
        if 1 <= idx <= len(actions):
            action = actions[idx - 1]
            return TurnChoice(action=action, reason="player choice")
        print("编号超出范围。")


def print_resolution(resolution) -> None:
    print()
    print(resolution.narrative)
    for bullet in resolution.bullet_points:
        print(f"- {bullet}")


def print_final(report: WorldReport) -> None:
    print("\n# 结局")
    print(f"- {report.ending_title} ({report.ending_id})")
    print(f"- ending_score: {report.ending_score}/100")
    print(f"- {report.ending_description}")
    print("\n# 最终世界状态")
    for key, value in report.final_state.items():
        initial = report.initial_state[key]
        delta = report.diff[key]
        sign = "+" if delta > 0 else ""
        print(f"- {key}: {initial} -> {value} ({sign}{delta})")
    print("\n# 世界总结")
    print(report.summary)
    print("\n# 可分享摘要")
    print(report.share_text)
    print("\n# Timeline")
    print(report.timeline_markdown)


if __name__ == "__main__":
    main()
