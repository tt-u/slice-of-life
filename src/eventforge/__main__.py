from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable

from eventforge.domain import ActionCard, FrozenInitialWorld, MaterialResearchPack, TurnChoice, WorldReport
from eventforge.engine import build_game
from eventforge.llm import OpenAICompatibleLLM
from eventforge.research import (
    build_cz_star_xu_public_conflict_frozen_world,
    build_cz_star_xu_public_conflict_research_pack,
    build_wuhan_university_yang_jingyuan_frozen_world,
    build_wuhan_university_yang_jingyuan_research_pack,
)
from eventforge.worldgen import build_scenario_from_material, inspect_material_seed

ResearchBuilder = Callable[[], MaterialResearchPack]
FrozenWorldBuilder = Callable[..., FrozenInitialWorld]

ANCHOR_CASES: dict[str, tuple[ResearchBuilder, FrozenWorldBuilder]] = {
    "wuhan-university-yang-jingyuan": (
        build_wuhan_university_yang_jingyuan_research_pack,
        build_wuhan_university_yang_jingyuan_frozen_world,
    ),
    "cz-star-xu-public-conflict": (
        build_cz_star_xu_public_conflict_research_pack,
        build_cz_star_xu_public_conflict_frozen_world,
    ),
}


def main() -> None:
    argv = sys.argv[1:]
    if argv and argv[0] in {"-h", "--help"}:
        print(build_overview_parser().format_help(), end="")
        return

    command = argv[0] if argv and argv[0] in {"play", "research-case", "freeze-world", "inspect-world"} else "play"
    command_argv = argv[1:] if command != "play" else (argv[1:] if argv and argv[0] == "play" else argv)
    parser = build_command_parser(command)
    args = parser.parse_args(command_argv)

    try:
        if command == "research-case":
            handle_research_case(args)
            return
        if command == "freeze-world":
            handle_freeze_world(args)
            return
        if command == "inspect-world":
            handle_inspect_world(args)
            return
        handle_play(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)


def build_overview_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m eventforge",
        description="slice-of-life game factory CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "commands:\n"
            "  play           load a frozen world or material and run a game\n"
            "  research-case  build a web-grounded anchor research pack\n"
            "  freeze-world   freeze an anchor case into an immutable world artifact\n"
            "  inspect-world  inspect a stored frozen world or anchor case\n\n"
            "examples:\n"
            "  python -m eventforge play --world-file examples/worlds/wuhan-university-yang-jingyuan-school.json --turns 4\n"
            "  python -m eventforge research-case --case wuhan-university-yang-jingyuan --output examples/research/wuhan-university-yang-jingyuan.json\n"
            "  python -m eventforge freeze-world --case cz-star-xu-public-conflict --player-role CZ --output /tmp/cz-world.json\n"
            "  python -m eventforge inspect-world --world-file /tmp/cz-world.json\n\n"
            "core play flags:\n"
            "  --world-file PATH\n"
            "  --material-file PATH\n"
            "  --player-role ROLE\n"
            "  --list-player-roles\n"
            "  --turns N\n"
        ),
    )
    return parser


def build_command_parser(command: str) -> argparse.ArgumentParser:
    if command == "research-case":
        parser = argparse.ArgumentParser(prog="python -m eventforge research-case", description="Build an anchor research pack")
        parser.add_argument("--case", required=True, choices=tuple(ANCHOR_CASES))
        parser.add_argument("--output", type=str, default=None)
        return parser

    if command == "freeze-world":
        parser = argparse.ArgumentParser(prog="python -m eventforge freeze-world", description="Freeze an anchor case into a world artifact")
        parser.add_argument("--case", required=True, choices=tuple(ANCHOR_CASES))
        parser.add_argument("--player-role", type=str, default=None)
        parser.add_argument("--output", type=str, required=True)
        return parser

    if command == "inspect-world":
        parser = argparse.ArgumentParser(prog="python -m eventforge inspect-world", description="Inspect a frozen world artifact")
        source_group = parser.add_mutually_exclusive_group(required=True)
        source_group.add_argument("--world-file", type=str, default=None)
        source_group.add_argument("--case", choices=tuple(ANCHOR_CASES), default=None)
        parser.add_argument("--player-role", type=str, default=None)
        return parser

    parser = argparse.ArgumentParser(prog="python -m eventforge play", description="Run a slice-of-life game")
    parser.add_argument("--mode", choices=("interactive", "auto"), default="interactive")
    parser.add_argument("--turns", type=int, default=6)
    parser.add_argument("--material-file", type=str, default=None)
    parser.add_argument("--world-file", type=str, default=None)
    parser.add_argument("--player-role", type=str, default=None)
    parser.add_argument("--list-player-roles", action="store_true")
    return parser


def handle_research_case(args: argparse.Namespace) -> None:
    pack = build_anchor_research_pack(args.case)
    if args.output:
        write_json_payload(Path(args.output), pack.to_payload())
        print(f"研究案例已写入：{args.output}")
    print(f"案例：{pack.title}")
    print(f"case_id：{pack.case_id}")
    print(f"可选视角：{' / '.join(pack.candidate_viewpoints)}")
    print(f"研究实体：{len(pack.entities)} | 实体卡：{len(pack.entity_cards)} | 争议点：{len(pack.disputed_points)}")
    if pack.research_notes:
        print(f"研究备注：{'；'.join(pack.research_notes)}")


def handle_freeze_world(args: argparse.Namespace) -> None:
    world = build_anchor_frozen_world(args.case, player_role=args.player_role)
    output_path = Path(args.output)
    write_json_payload(output_path, world.to_payload())
    print(f"冻结世界已写入：{output_path}")
    print(f"世界：{world.title}")
    print(f"世界ID：{world.world_id}")
    print(f"玩家视角：{world.player_role}")
    print(f"允许回合：{' / '.join(str(item) for item in world.allowed_turn_counts)}")


def handle_inspect_world(args: argparse.Namespace) -> None:
    world = load_frozen_world(Path(args.world_file)) if args.world_file else build_anchor_frozen_world(args.case, player_role=args.player_role)
    print_world_inspection(world)


def handle_play(args: argparse.Namespace) -> None:
    try:
        if args.world_file:
            frozen_world = load_frozen_world(Path(args.world_file))
            if args.player_role and args.player_role != frozen_world.player_role:
                raise ValueError(
                    f"World file {args.world_file} is already frozen for role {frozen_world.player_role}; "
                    "freeze a new world artifact for a different viewpoint instead."
                )
            if args.list_player_roles:
                print(f"# 可选玩家角色：{frozen_world.title}")
                print(f"当前选择：{frozen_world.player_role}")
                print(f"可选视角：{' / '.join(frozen_world.selectable_roles)}")
                print(f"允许回合：{' / '.join(str(item) for item in frozen_world.allowed_turn_counts)}")
                return
            llm_client = OpenAICompatibleLLM()
            game = build_game(turns=args.turns, llm_client=llm_client, frozen_world=frozen_world)
        elif args.material_file:
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
        raise SystemExit(1) from exc
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

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


def build_anchor_research_pack(case_id: str) -> MaterialResearchPack:
    research_builder, _ = ANCHOR_CASES[case_id]
    return research_builder()


def build_anchor_frozen_world(case_id: str, *, player_role: str | None = None) -> FrozenInitialWorld:
    pack = build_anchor_research_pack(case_id)
    _, frozen_builder = ANCHOR_CASES[case_id]
    chosen_role = player_role or pack.candidate_viewpoints[0]
    return frozen_builder(player_role=chosen_role)


def load_frozen_world(path: Path) -> FrozenInitialWorld:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return FrozenInitialWorld.from_payload(payload)


def write_json_payload(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def print_world_inspection(world: FrozenInitialWorld) -> None:
    dimension_parts = []
    initial_dimensions = world.initial_dimension_map()
    for dimension in world.resolved_dimension_defs()[:6]:
        dimension_parts.append(f"{dimension.label} {initial_dimensions[dimension.key]}")

    print(f"# 冻结世界检查：{world.title}")
    print(f"世界ID：{world.world_id}")
    print(f"玩家视角：{world.player_role}")
    print(f"可选视角：{' / '.join(world.selectable_roles)}")
    print(f"允许回合：{' / '.join(str(item) for item in world.allowed_turn_counts)}")
    print(f"玩家目标：{world.objective}")
    print(f"玩家真相：{world.player_secret}")
    print(f"主要对位：{world.opponent}")
    print(f"开局事件：{world.opening_event.headline}")
    print(world.opening_event.summary)
    print(f"初始剖面：{' / '.join(dimension_parts)}")
    print("终局标签：")
    for band in world.ending_bands:
        print(f"- {band.label} ({band.ending_id}) >= {band.min_score}")


def print_intro(game) -> None:
    world = game.frozen_world
    print(f"# {world.title}")
    print()
    print(world.premise)
    print()
    print(f"你扮演：{world.player_role}")
    print(f"意图：{world.objective}")
    print(f"对手：{world.opponent}")
    print(f"真相：{world.player_secret}")
    if world.selectable_roles:
        print(f"可选视角：{' / '.join(world.selectable_roles)}")
    print()
    print(f"开局事件：{world.opening_event.headline}")
    print(world.opening_event.summary)
    print("开局剖面：" + summarize_initial_world(game))
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


def summarize_initial_world(game) -> str:
    return format_dimension_snapshot(
        game,
        separator=" / ",
        fallback_keys=("control", "pressure", "credibility", "narrative_control"),
    )


def format_dimension_snapshot(
    game,
    *,
    separator: str = " | ",
    limit: int | None = None,
    fallback_keys: tuple[str, ...] = ("control", "pressure", "credibility", "narrative_control"),
) -> str:
    frozen_world = getattr(game, "frozen_world", None)
    dimension_defs = getattr(frozen_world, "resolved_dimension_defs", lambda: ())()
    state = game.state
    if not dimension_defs:
        fallback_labels = {
            "control": "控制权",
            "pressure": "压力",
            "credibility": "公信力",
            "narrative_control": "叙事控制",
            "community_panic": "社区恐慌",
            "exchange_trust": "交易所信任",
            "price": "币价",
            "treasury": "国库",
        }
        parts = [f"{fallback_labels.get(key, key)} {getattr(state, key)}" for key in fallback_keys]
        return separator.join(parts[:limit] if limit is not None else parts)

    parts = [f"{dimension.label} {getattr(state, dimension.key)}" for dimension in dimension_defs]
    if limit is not None:
        parts = parts[:limit]
    return separator.join(parts)


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
        format_dimension_snapshot(
            game,
            separator=" | ",
            limit=6,
            fallback_keys=("control", "narrative_control", "community_panic", "exchange_trust", "price", "treasury"),
        )
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
