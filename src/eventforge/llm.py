from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any
from urllib import request

from .domain import AgentProfile, ScenarioBlueprint, SeedEntity, WorldEvent, WorldState


@dataclass(slots=True)
class URLTransport:
    timeout: int = 30

    def create_chat_completion(self, *, base_url: str, api_key: str, model: str, messages: list[dict[str, str]], temperature: float) -> dict[str, Any]:
        payload = json.dumps(
            {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "response_format": {"type": "json_object"},
            }
        ).encode("utf-8")
        req = request.Request(
            url=base_url.rstrip("/") + "/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))


class OpenAICompatibleLLM:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        transport: Any | None = None,
    ) -> None:
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = temperature
        self.transport = transport or URLTransport()
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        missing = []
        if not self.api_key:
            missing.append("OPENAI_API_KEY")
        if not self.base_url:
            missing.append("OPENAI_BASE_URL")
        if not self.model:
            missing.append("OPENAI_MODEL")
        if missing:
            raise ValueError(f"Missing LLM configuration: {', '.join(missing)}")

    def generate_agent_profile(self, *, entity: SeedEntity, scenario_title: str, world_truth: str) -> AgentProfile:
        messages = [
            {
                "role": "system",
                "content": (
                    "Return json only. You expand one seed entity into a playable crisis-simulation agent. "
                    "Keys: private_fear, voice, stance, trust_in_player, influence. "
                    "trust_in_player and influence must be integers 0-100."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "scenario_title": scenario_title,
                        "world_truth": world_truth,
                        "entity": {
                            "id": entity.id,
                            "name": entity.name,
                            "role": entity.role,
                            "public_goal": entity.public_goal,
                            "pressure_point": entity.pressure_point,
                            "starting_trust": entity.starting_trust,
                            "influence": entity.influence,
                            "stance": entity.stance,
                            "details": entity.details,
                        },
                        "instruction": "Return json only.",
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        payload = self.transport.create_chat_completion(
            base_url=self.base_url,
            api_key=self.api_key or "",
            model=self.model,
            messages=messages,
            temperature=self.temperature,
        )
        content = payload["choices"][0]["message"]["content"]
        data = json.loads(content)
        return AgentProfile(
            id=entity.id,
            name=entity.name,
            role=entity.role,
            public_goal=entity.public_goal,
            private_fear=str(data["private_fear"]),
            pressure_point=entity.pressure_point,
            voice=str(data["voice"]),
            stance=str(data["stance"]),
            trust_in_player=_clamp_int(data["trust_in_player"]),
            influence=_clamp_int(data["influence"]),
            source_seed_id=entity.id,
        )

    def generate_scenario_blueprint(self, *, source_material: str, entity_cap: int, selected_player_role: str | None = None) -> ScenarioBlueprint:
        if os.getenv("EVENTFORGE_TEST_STUB_BLUEPRINT") == "1":
            chosen_role = selected_player_role or "校方"
            initial_world = (
                WorldState(credibility=43, treasury=58, pressure=79, price=44, liquidity=50, sell_pressure=66, volatility=71, community_panic=70, rumor_level=74, narrative_control=31, exchange_trust=40, control=61)
                if chosen_role == "校方"
                else WorldState(credibility=28, treasury=42, pressure=90, price=44, liquidity=50, sell_pressure=66, volatility=75, community_panic=82, rumor_level=86, narrative_control=47, exchange_trust=35, control=26)
            )
            return ScenarioBlueprint(
                title="测试事件",
                premise="测试用多视角场景。",
                player_role=chosen_role,
                player_secret="测试真相。",
                objective="测试目标。",
                opponent="测试对手。",
                audience=("公众",),
                truth="测试事实。",
                opening_event=WorldEvent(headline="测试开局", summary="测试摘要。", severity=70),
                entities=(
                    SeedEntity("school", "武汉大学校方", "校方", "恢复秩序", "回应滞后", 45, 90, "defensive", "学校治理主体"),
                    SeedEntity("yang", "杨景媛", "杨景媛", "维护个人叙事", "持续承压", 36, 85, "embattled", "直接冲突当事人"),
                ),
                initial_world=initial_world,
                playable_roles=("校方", "杨景媛"),
            )
        messages = [
            {
                "role": "system",
                "content": (
                    "Return json only. Turn the provided source material into a playable crisis-simulation scenario blueprint. "
                    "Keys: title, premise, player_role, playable_roles, player_secret, objective, opponent, audience, truth, opening_event, entities, initial_world. "
                    "Use no more than the requested entity_cap entities. derive entity roles from the material itself instead of forcing a fixed taxonomy. "
                    "If selected_player_role is provided, treat it as the mandatory playable viewpoint and make the entire initial world relative to that choice. "
                    "If the material contains multiple direct conflict parties, they may each be valid playable viewpoints, but the returned player_role and initial_world must correspond to the selected one. "
                    "When two opposing parties could both be selected, make at least 3 core world metrics materially different across viewpoints rather than only changing the label. "
                    "player_role should name the playable role directly; for institution-side play prefer concise roles like 校方 / 平台 / 公司, not 校方核心决策者-style labels. "
                    "initial_world must be relative to the chosen player_role: the same incident should produce meaningfully different starting values if the player role changes. "
                    "Entities should be neutral stakeholder groups, not sentiment-split duplicates; do not create separate entities like 支持X的声音 and 反对X的声音 when both belong to one broader public group. "
                    "audience must be an array of strings. opening_event must be an object with headline, summary, severity. "
                    "Each entity must include id, name, role, public_goal, pressure_point, starting_trust, influence, stance, details. "
                    "initial_world must contain: credibility, treasury, pressure, price, liquidity, sell_pressure, volatility, community_panic, rumor_level, narrative_control, exchange_trust, control."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "entity_cap": entity_cap,
                        "source_material": source_material,
                        "selected_player_role": selected_player_role,
                        "instruction": "Return json only.",
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        payload = self.transport.create_chat_completion(
            base_url=self.base_url,
            api_key=self.api_key or "",
            model=self.model,
            messages=messages,
            temperature=0.8,
        )
        content = payload["choices"][0]["message"]["content"]
        data = json.loads(content)
        opening_event = _coerce_opening_event(data.get("opening_event"), fallback_premise=str(data.get("premise", "")))
        initial_world_data = data["initial_world"]
        return ScenarioBlueprint(
            title=str(data["title"]),
            premise=str(data["premise"]),
            player_role=str(data["player_role"]),
            player_secret=str(data["player_secret"]),
            objective=str(data["objective"]),
            opponent=str(data["opponent"]),
            audience=_coerce_audience(data.get("audience")),
            truth=str(data["truth"]),
            opening_event=opening_event,
            entities=tuple(_coerce_seed_entity(item) for item in data["entities"]),
            initial_world=WorldState(
                credibility=_clamp_int(initial_world_data["credibility"]),
                treasury=_clamp_int(initial_world_data["treasury"]),
                pressure=_clamp_int(initial_world_data["pressure"]),
                price=_clamp_int(initial_world_data["price"]),
                liquidity=_clamp_int(initial_world_data["liquidity"]),
                sell_pressure=_clamp_int(initial_world_data["sell_pressure"]),
                volatility=_clamp_int(initial_world_data["volatility"]),
                community_panic=_clamp_int(initial_world_data["community_panic"]),
                rumor_level=_clamp_int(initial_world_data["rumor_level"]),
                narrative_control=_clamp_int(initial_world_data["narrative_control"]),
                exchange_trust=_clamp_int(initial_world_data["exchange_trust"]),
                control=_clamp_int(initial_world_data["control"]),
            ),
            playable_roles=_coerce_playable_roles(data.get("playable_roles"), player_role=str(data["player_role"]), selected_player_role=selected_player_role),
        )

    def generate_turn_actions(
        self,
        *,
        scenario_title: str,
        player_role: str,
        player_objective: str,
        state_summary: dict[str, int],
        decision_focus: list[dict[str, int | str]],
        available_templates: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        messages = [
            {
                "role": "system",
                "content": (
                    "Return json only. Generate 4 player choices for the next turn of a crisis simulation. "
                    "Key: actions. Each action needs template_id, label, description. "
                    "template_id must be chosen from the provided templates. "
                    "Each template includes impact_tier, impact_cost, upside_axes, and downside_axes. "
                    "Every choice must read like a tradeoff: +A / -B, with explicit upside and explicit cost. "
                    "Make the description itself end with a compact explicit tradeoff like （+叙事控制 / -压力）. "
                    "Work backward from the player objective and the current state weaknesses in decision_focus. "
                    "Hard constraints: prefer a spread of impact tiers, include a low-tier option and a medium-tier option when available, and avoid returning more than one extreme-tier option."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "scenario_title": scenario_title,
                        "player_role": player_role,
                        "player_objective": player_objective,
                        "state_summary": state_summary,
                        "decision_focus": decision_focus,
                        "available_templates": available_templates,
                        "instruction": "Return json only.",
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        payload = self.transport.create_chat_completion(
            base_url=self.base_url,
            api_key=self.api_key or "",
            model=self.model,
            messages=messages,
            temperature=0.9,
        )
        content = payload["choices"][0]["message"]["content"]
        data = json.loads(content)
        actions = data["actions"]
        if not isinstance(actions, list) or len(actions) < 2:
            raise ValueError("LLM must return at least two actions")
        return [
            {
                "template_id": str(item["template_id"]),
                "label": str(item["label"]),
                "description": str(item["description"]),
            }
            for item in actions
        ]

    def narrate_turn(
        self,
        *,
        turn_number: int,
        action_label: str,
        player_objective: str,
        state_summary: dict[str, int],
        agent_profiles: list[AgentProfile],
    ) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "Return json only. Write one concise crisis update in Chinese. "
                    "Key: narrative. Mention player action and at least two world reactions."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "turn_number": turn_number,
                        "action_label": action_label,
                        "player_objective": player_objective,
                        "state_summary": state_summary,
                        "agents": [
                            {
                                "name": profile.name,
                                "role": profile.role,
                                "stance": profile.stance,
                                "trust_in_player": profile.trust_in_player,
                                "influence": profile.influence,
                            }
                            for profile in agent_profiles
                        ],
                        "instruction": "Return json only.",
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        payload = self.transport.create_chat_completion(
            base_url=self.base_url,
            api_key=self.api_key or "",
            model=self.model,
            messages=messages,
            temperature=0.8,
        )
        content = payload["choices"][0]["message"]["content"]
        return str(json.loads(content)["narrative"])

    def summarize_world_state(
        self,
        *,
        scenario_title: str,
        player_role: str,
        initial_state: dict[str, int],
        final_state: dict[str, int],
        diff: dict[str, int],
        timeline: list[str],
    ) -> tuple[str, str]:
        messages = [
            {
                "role": "system",
                "content": (
                    "Return json only. Summarize the final world state of a simulation in Chinese. "
                    "Keys: summary, share_text. share_text should be compact and easy to copy/share."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "scenario_title": scenario_title,
                        "player_role": player_role,
                        "initial_state": initial_state,
                        "final_state": final_state,
                        "diff": diff,
                        "timeline": timeline,
                        "instruction": "Return json only.",
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        payload = self.transport.create_chat_completion(
            base_url=self.base_url,
            api_key=self.api_key or "",
            model=self.model,
            messages=messages,
            temperature=0.6,
        )
        content = payload["choices"][0]["message"]["content"]
        data = json.loads(content)
        return str(data["summary"]), str(data["share_text"])


def _clamp_int(value: Any) -> int:
    if isinstance(value, bool):
        numeric = int(value)
    elif isinstance(value, (int, float)):
        numeric = int(value)
    elif isinstance(value, str):
        text = value.strip().lower()
        adjective_map = {
            "critical": 85,
            "extreme": 90,
            "high": 75,
            "medium": 55,
            "moderate": 55,
            "low": 30,
        }
        if text in adjective_map:
            numeric = adjective_map[text]
        else:
            match = re.search(r"-?\d+", text)
            numeric = int(match.group(0)) if match else 0
    else:
        numeric = 0
    return max(0, min(100, numeric))


def _coerce_audience(value: Any) -> tuple[str, ...]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
    elif isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
    else:
        items = []
    return tuple(items or ("公众", "关键利益相关方"))


def _coerce_playable_roles(value: Any, *, player_role: str, selected_player_role: str | None = None) -> tuple[str, ...]:
    roles: list[str] = []
    if isinstance(value, list):
        roles = [str(item).strip() for item in value if str(item).strip()]
    elif isinstance(value, str) and value.strip():
        roles = [item.strip() for item in value.split(",") if item.strip()]
    fallback = selected_player_role or player_role
    if fallback and fallback not in roles:
        roles.insert(0, fallback)
    if player_role and player_role not in roles:
        roles.append(player_role)
    deduped: list[str] = []
    for role in roles:
        if role not in deduped:
            deduped.append(role)
    return tuple(deduped or (player_role,))


def _coerce_opening_event(value: Any, *, fallback_premise: str) -> WorldEvent:
    if isinstance(value, dict):
        return WorldEvent(
            headline=str(value.get("headline") or "危机升级"),
            summary=str(value.get("summary") or fallback_premise or "事件开始快速发酵。"),
            severity=_clamp_int(value.get("severity", 70)),
        )
    text = str(value or fallback_premise or "事件开始快速发酵。")
    headline = text.split("。", 1)[0][:32] or "危机升级"
    return WorldEvent(headline=headline, summary=text, severity=70)


def _coerce_seed_entity(item: dict[str, Any]) -> SeedEntity:
    description = str(item.get("details") or item.get("description") or item.get("public_goal") or item.get("name") or "")
    return SeedEntity(
        id=str(item.get("id") or item.get("name") or "entity"),
        name=str(item.get("name") or item.get("id") or "Entity"),
        role=str(item.get("role") or "community"),
        public_goal=str(item.get("public_goal") or description or "protect their position"),
        pressure_point=str(item.get("pressure_point") or "public scrutiny"),
        starting_trust=_clamp_int(item.get("starting_trust", 35)),
        influence=_clamp_int(item.get("influence", 55)),
        stance=str(item.get("stance") or "watching"),
        details=description or "generated from source material",
    )
