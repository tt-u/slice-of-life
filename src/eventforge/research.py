from __future__ import annotations

from .domain import (
    EntityResearchCard,
    EvidenceNote,
    FrozenInitialWorld,
    MaterialResearchPack,
    ResearchDispute,
    ResearchRelationship,
    SeedEntity,
    WorldDimensionDef,
    WorldEndingBand,
    WorldEvent,
    default_agent_reaction_boundaries,
    dimension_driven_world_action_grammar,
)

WHU_NOTICE_URL = "https://www.whu.edu.cn/info/5231/258444.htm"
WHU_NOTICE_TITLE = "武汉大学情况通报"
CZ_STAR_XU_COINTELEGRAPH_URL = "https://cointelegraph.com/news/cz-memoir-reignites-feud-with-okx-star-xu"
CZ_STAR_XU_COINTELEGRAPH_TITLE = "CZ memoir revives feud with OKX founder Star Xu over contract forgery, Huobi arrest"
STAR_XU_DENIAL_URL = "https://x.com/star_okx/status/2041754856814235695"
STAR_XU_LIAR_URL = "https://x.com/star_okx/status/2041785361807114422"


def build_cz_star_xu_public_conflict_research_pack() -> MaterialResearchPack:
    cointelegraph_note = EvidenceNote(
        source_title=CZ_STAR_XU_COINTELEGRAPH_TITLE,
        source_url=CZ_STAR_XU_COINTELEGRAPH_URL,
        note=(
            "Cointelegraph 2026-04-08 报道：CZ 新回忆录再次点燃与徐明星的长期公开冲突，"
            "争议聚焦 OKCoin 旧合约伪造指控、徐明星是否举报李林，以及 2020 年 OKEx 暂停提币。"
        ),
    )
    star_xu_denial = EvidenceNote(
        source_title="Star Xu X post denying Huobi informant allegation",
        source_url=STAR_XU_DENIAL_URL,
        note=(
            "徐明星在 X 上称 CZ 书中关于其举报李林的说法“纯属不实信息”，"
            "并强调大型平台每年都会遭遇大量举报投诉，举报本身并不能决定执法结果。"
        ),
    )
    star_xu_counterattack = EvidenceNote(
        source_title="Star Xu X post calling CZ a habitual liar",
        source_url=STAR_XU_LIAR_URL,
        note=(
            "徐明星在 X 上点名称 CZ 为“habitual liar”，把冲突重新拉回 OKCoin 入离职历史、"
            "Roger Ver 合约争议、是否操纵市场，以及是否在调查中充当污点证人等多条旧案。"
        ),
    )

    entity_cards = (
        EntityResearchCard(
            entity_id="cz-binance",
            name="CZ 与 Binance 叙事面",
            role="CZ",
            stance="借回忆录重写旧纠纷并捍卫自身创业史叙事",
            public_position="CZ 在新书中称自己曾在 OKCoin 合约纠纷和后续行业冲突中遭遇 FUD，并把 2020 年提币暂停旧案再度归因到徐明星一侧。",
            conflict_stakes="核心利害是个人可信度、Binance 历史正当性，以及其能否继续主导这场行业旧账的解释框架。",
            notable_pressures=("回忆录被质疑借个人叙事翻旧账", "被指长期重复有利于自身的版本", "任何证据缺口都会伤害其公信力"),
            relationships=(
                ResearchRelationship("star-xu-okx", "direct-conflict", "与徐明星/OKX 阵营围绕旧合约、举报传闻和提币冻结责任展开正面冲突。"),
                ResearchRelationship("roger-ver-contract", "legacy-contract", "其离开 OKCoin 时的 Roger Ver 合约版本差异被重新搬上台面。"),
                ResearchRelationship("market-watchers", "narrative-contest", "需要说服行业围观者相信自己的回忆录版本不是选择性叙事。"),
            ),
            evidence=(cointelegraph_note,),
        ),
        EntityResearchCard(
            entity_id="star-xu-okx",
            name="徐明星与 OKX 阵营",
            role="徐明星/OKX camp",
            stance="公开反击并试图把冲突定义为 CZ 再次散播失实叙事",
            public_position="徐明星连续发帖否认举报李林、质疑 CZ 的旧合约说法，并称其在 OKCoin 历史、市场操纵和婚姻等问题上都在说谎。",
            conflict_stakes="核心利害是徐明星个人信誉、OKX 治理能力以及交易平台在旧案阴影下的品牌稳定性。",
            notable_pressures=("2020 年提币暂停旧案再次被翻出", "举报传闻与污点证人指控同时压来", "若拿不出新证据容易被视为情绪化反击"),
            relationships=(
                ResearchRelationship("cz-binance", "direct-conflict", "与 CZ 围绕历史版本、证据可信度和谁在操纵行业舆论进行正面对撞。"),
                ResearchRelationship("leon-li-huobi", "informant-dispute", "被卷入是否向 authorities 举报李林的传闻链条。"),
                ResearchRelationship("market-watchers", "trust-defense", "必须稳住用户与观察者对 OKX 治理与钱包架构的信心。"),
            ),
            evidence=(star_xu_denial, star_xu_counterattack, cointelegraph_note),
        ),
        EntityResearchCard(
            entity_id="leon-li-huobi",
            name="李林与火币旧案旁证",
            role="行业旧案证人",
            stance="本体并未正面下场，但其名字成为举报传闻与平台治理比较的关键支点",
            public_position="Cointelegraph 转述 CZ 书中说法：李林曾认为徐明星早年举报过自己；徐明星则公开否认该指控。",
            conflict_stakes="核心利害在于其名字被当作旧案真伪的佐证节点，会放大行业内部举报与执法想象。",
            notable_pressures=("本人并非当前冲突主角却被不断引用", "旧案传闻缺乏完全可验证的一手公开证据"),
            relationships=(
                ResearchRelationship("star-xu-okx", "informant-rumor", "关于徐明星是否举报李林的说法使其成为徐明星反击的关键参照物。"),
                ResearchRelationship("cz-binance", "memoir-reference", "CZ 借其转述来强化自己对徐明星的旧案指控。"),
            ),
            evidence=(cointelegraph_note, star_xu_denial),
        ),
        EntityResearchCard(
            entity_id="roger-ver-contract",
            name="Roger Ver / OKCoin 合约旧案",
            role="历史证据场",
            stance="作为 2014-2015 年合约版本争议的证据池，被双方重新调用",
            public_position="Cointelegraph 报道称徐明星再次搬出 OKCoin 当年发布的公证聊天视频和 Reddit 声明，用来指控 CZ 在 Roger Ver 合约上伪造版本或签名。",
            conflict_stakes="核心利害在于旧合同与聊天记录的解释权，因为它直接影响谁在这场长期冲突里更像叙事操纵者。",
            notable_pressures=("旧材料年代久远且解释空间大", "一旦被重新传播就会快速污染当前品牌评价"),
            relationships=(
                ResearchRelationship("cz-binance", "evidence-pressure", "旧合约材料持续给 CZ 的回忆录叙事施压。"),
                ResearchRelationship("star-xu-okx", "evidence-weapon", "徐明星把它作为证明 CZ 不可信的核心武器。"),
            ),
            evidence=(cointelegraph_note, star_xu_counterattack),
        ),
        EntityResearchCard(
            entity_id="market-watchers",
            name="交易平台用户与行业围观者",
            role="市场舆论",
            stance="既消费八卦，又会把创始人互撕直接投射为平台治理风险",
            public_position="公众关注的不只是旧账真假，还包括创始人互撕是否会伤害 Binance、OKX 以及亚洲交易平台整体治理形象。",
            conflict_stakes="核心利害是把个人旧怨和平台安全、治理、信任风险连在一起，导致事件迅速从口水战升级为品牌风控问题。",
            notable_pressures=("对钱包架构、治理透明度与创始人诚信高度敏感", "会把旧案重新传播成新的平台信任冲击"),
            relationships=(
                ResearchRelationship("cz-binance", "credibility-judgment", "围观者会把 CZ 的回忆录视作自证还是再造叙事。"),
                ResearchRelationship("star-xu-okx", "governance-judgment", "围观者会把徐明星的反击与 2020 年提币暂停旧案绑定解读。"),
            ),
            evidence=(cointelegraph_note,),
        ),
    )

    entities = (
        SeedEntity(
            id="cz-binance",
            name="CZ 与 Binance 叙事面",
            role="CZ",
            public_goal="守住个人创业史版本并避免被定性为反复翻旧账的操盘者",
            pressure_point="任何被核实的旧案矛盾都会反噬其回忆录可信度",
            starting_trust=46,
            influence=94,
            stance="主动出击",
            details="拥有巨大的行业注意力和传播能力，但越主动翻旧账越容易被要求拿出硬证据。",
        ),
        SeedEntity(
            id="star-xu-okx",
            name="徐明星与 OKX 阵营",
            role="徐明星/OKX camp",
            public_goal="把冲突重新定义为对 CZ 失实叙事的公开纠偏",
            pressure_point="提币冻结旧案与举报传闻同时拖累平台治理形象",
            starting_trust=39,
            influence=88,
            stance="高压反击",
            details="既要维护徐明星本人信誉，也要避免 OKX 被再次读成治理脆弱的平台。",
        ),
        SeedEntity(
            id="leon-li-huobi",
            name="李林与火币旧案旁证",
            role="行业旧案证人",
            public_goal="避免自己的旧案被持续当作别人互攻弹药",
            pressure_point="名字被反复当作举报传闻的证明或反证明",
            starting_trust=34,
            influence=63,
            stance="被动卷入",
            details="虽然不是当前正面冲突双方，却是举报传闻链里最容易被借用的支点。",
        ),
        SeedEntity(
            id="roger-ver-contract",
            name="Roger Ver / OKCoin 合约旧案",
            role="历史证据场",
            public_goal="迫使双方回到可核查的旧记录上",
            pressure_point="旧证据越碎片化，越容易被任何一方剪裁利用",
            starting_trust=31,
            influence=58,
            stance="证据回流",
            details="不属于独立人物阵营，而是会不断回流到当下叙事中的旧证据集合。",
        ),
        SeedEntity(
            id="market-watchers",
            name="交易平台用户与行业围观者",
            role="市场舆论",
            public_goal="判断谁在撒谎以及平台治理是否因此存在真实风险",
            pressure_point="碎片化旧案让他们更容易用情绪化结论替代细节判断",
            starting_trust=22,
            influence=91,
            stance="高热围观",
            details="一旦把冲突理解为平台治理风险，而不只是创始人口角，外溢杀伤会迅速放大。",
        ),
    )

    disputes = (
        ResearchDispute(
            key="contract-forgery",
            claim="CZ 在离开 OKCoin 时是否伪造或篡改过 Roger Ver 合约版本/签名",
            sides=("CZ 的自述与回忆录版本", "徐明星/OKCoin 旧证据与反驳版本"),
            status="contested",
        ),
        ResearchDispute(
            key="informant-rumor",
            claim="徐明星是否曾向 authorities 举报李林并导致旧案执法后果",
            sides=("CZ 书中转述与围观传闻", "徐明星公开否认的一方"),
            status="active",
        ),
        ResearchDispute(
            key="withdrawal-governance",
            claim="2020 年 OKEx 提币暂停究竟反映徐明星个人控制钱包还是更广泛的治理设计问题",
            sides=("认为徐明星/OKX 治理架构失当的一方", "认为 CZ 借旧案夸大平台失序的一方"),
            status="contested",
        ),
    )

    return MaterialResearchPack(
        case_id="cz-star-xu-public-conflict",
        title="CZ / 徐明星公开冲突",
        source_material=(
            "以 2026-04-08 Cointelegraph 对 CZ 新回忆录与徐明星公开反击的报道为主线，"
            "结合徐明星在 X 上的两条回应，整理 OKCoin 合约旧案、举报传闻与 2020 年提币暂停的冲突结构。"
        ),
        premise="一本回忆录把十多年行业旧账重新抛回台面，让 CZ 与徐明星/OKX 阵营再次公开互撕。",
        opponent="对位创始人阵营、会把创始人口角直接映射成平台治理风险的市场围观者，以及难以彻底验证的旧案证据",
        audience=("交易平台用户", "行业从业者", "加密媒体读者", "二级市场围观者"),
        truth="这不是单纯的嘴仗，而是个人回忆录、旧案证据、平台治理历史与行业信任同时争夺解释权的复合冲突。",
        entities=entities,
        candidate_viewpoints=("CZ", "徐明星/OKX camp"),
        opening_event=WorldEvent(
            headline="回忆录与 X 贴文把旧案重新点燃",
            summary="CZ 新书与徐明星连续发帖互相指控，把合约伪造、举报传闻和提币冻结旧案一起拉回公众视野。",
            severity=82,
            actor_id="cz-binance",
            actor_name="CZ 与 Binance 叙事面",
        ),
        research_notes=(
            "当前研究包以 Cointelegraph 报道和徐明星本人 X 帖为第一版公开证据基线。",
            "首批可玩角色限定为直接正面对撞的 CZ 与徐明星/OKX camp；李林与 Roger Ver 合约旧案保留为高影响旁证节点。",
            "后续冻结世界时必须保留合约真伪、举报传闻与平台治理可信度这三条主冲突轴。",
        ),
        entity_cards=entity_cards,
        disputed_points=disputes,
    )


def build_cz_star_xu_public_conflict_frozen_world(*, player_role: str = "CZ") -> FrozenInitialWorld:
    pack = build_cz_star_xu_public_conflict_research_pack()
    normalized_role = _normalize_cz_star_xu_player_role(player_role)
    initial_dimensions = _cz_star_xu_initial_dimensions_for_role(normalized_role)
    dimension_defs = _cz_star_xu_dimension_defs()
    objective = _cz_star_xu_objective_for_role(normalized_role)
    player_secret = _cz_star_xu_player_secret_for_role(normalized_role)
    opponent = _cz_star_xu_opponent_for_role(normalized_role)
    action_grammar = dimension_driven_world_action_grammar(
        initial_dimensions,
        dimension_defs,
        player_role=normalized_role,
        objective=objective,
    )

    return FrozenInitialWorld(
        world_id=f"{pack.case_id}-{'cz' if normalized_role == 'CZ' else 'star-xu-okx-camp'}",
        title=pack.title,
        premise=pack.premise,
        player_role=normalized_role,
        player_secret=player_secret,
        objective=objective,
        opponent=opponent,
        audience=pack.audience,
        truth=pack.truth,
        selectable_roles=pack.candidate_viewpoints,
        allowed_turn_counts=(4, 6, 8, 10),
        opening_event=pack.opening_event,
        initial_dimensions=tuple(initial_dimensions.items()),
        entities=pack.entities,
        ending_bands=_cz_star_xu_ending_bands(),
        dimension_defs=dimension_defs,
        action_grammar=action_grammar,
        reaction_boundaries=default_agent_reaction_boundaries(),
    )


def _normalize_cz_star_xu_player_role(player_role: str) -> str:
    normalized = player_role.strip()
    if normalized not in {"CZ", "徐明星/OKX camp"}:
        raise ValueError(f"Unsupported CZ / Star Xu anchor role: {player_role}")
    return normalized


def _cz_star_xu_initial_dimensions_for_role(player_role: str) -> dict[str, int]:
    by_role = {
        "CZ": {
            "credibility": 54,
            "treasury": 68,
            "pressure": 58,
            "price": 63,
            "liquidity": 61,
            "sell_pressure": 52,
            "volatility": 66,
            "community_panic": 49,
            "rumor_level": 72,
            "narrative_control": 47,
            "exchange_trust": 56,
            "control": 71,
        },
        "徐明星/OKX camp": {
            "credibility": 41,
            "treasury": 52,
            "pressure": 76,
            "price": 67,
            "liquidity": 46,
            "sell_pressure": 61,
            "volatility": 74,
            "community_panic": 63,
            "rumor_level": 78,
            "narrative_control": 58,
            "exchange_trust": 43,
            "control": 55,
        },
    }
    return dict(by_role[player_role])


def _cz_star_xu_dimension_defs() -> tuple[WorldDimensionDef, ...]:
    return (
        WorldDimensionDef("credibility", "可信度", "玩家阵营当前版本能否被行业与媒体当作更可信的叙事。", "higher_is_better", 60, 40, 20),
        WorldDimensionDef("treasury", "资源余量", "还能调动多少平台资源、人脉与证据渠道继续打这场旧账。", "higher_is_better", 50, 30, 15),
        WorldDimensionDef("pressure", "承压值", "来自对位创始人、媒体追问和旧案回流的即时压强。", "lower_is_better", 50, 70, 85),
        WorldDimensionDef("price", "热度位", "这场冲突在加密舆论场中占据了多少注意力。", "lower_is_better", 50, 68, 84),
        WorldDimensionDef("liquidity", "腾挪空间", "你还能否切换证据、口径与动作，而不是被单一叙事锁死。", "higher_is_better", 55, 35, 20),
        WorldDimensionDef("sell_pressure", "抛压联想", "围观者是否开始把口水战映射成平台风险和交易抛压。", "lower_is_better", 45, 60, 80),
        WorldDimensionDef("volatility", "情绪波动", "围观情绪是否在新爆料、旧截图和二次传播中持续抽搐。", "lower_is_better", 45, 65, 80),
        WorldDimensionDef("community_panic", "用户惊惧", "交易平台用户是否把创始人互撕读成真实治理风险。", "lower_is_better", 40, 58, 76),
        WorldDimensionDef("rumor_level", "旧案噪声", "未经完整核验的旧合约、举报传闻和黑历史回流强度。", "lower_is_better", 42, 62, 80),
        WorldDimensionDef("narrative_control", "叙事控制", "玩家阵营能否主导公众把冲突理解成哪一种故事。", "higher_is_better", 58, 38, 22),
        WorldDimensionDef("exchange_trust", "平台信任", "外界是否相信相关平台仍具备稳定治理与风控能力。", "higher_is_better", 58, 40, 22),
        WorldDimensionDef("control", "节奏掌控", "玩家阵营对爆料节奏、证据投放和后续攻防的控制程度。", "higher_is_better", 60, 40, 22),
    )


def _cz_star_xu_ending_bands() -> tuple[WorldEndingBand, ...]:
    return (
        WorldEndingBand(80, "cz-star-xu-narrative-suppression", "叙事压制", "你压住了最致命的旧案回流，让市场暂时接受了你的版本，冲突仍在但主导权归你。"),
        WorldEndingBand(55, "cz-star-xu-fractured-stalemate", "裂痕僵持", "双方都没能彻底击穿对面，旧账继续悬着，平台与个人信誉一起带伤前行。"),
        WorldEndingBand(30, "cz-star-xu-credibility-backlash", "信誉反噬", "你想借旧案压制对手，却让更多围观者把矛头转向你的证据缺口和治理伤口。"),
        WorldEndingBand(0, "cz-star-xu-platform-adrift", "平台失锚", "争吵已经不再只是创始人恩怨，市场开始把它读成平台治理系统性失锚。"),
    )


def _cz_star_xu_objective_for_role(player_role: str) -> str:
    if player_role == "CZ":
        return "在重提旧案时守住自己版本的可信度，并避免冲突被重新解释成你借回忆录操纵叙事。"
    return "把事件重新定义为对 CZ 失实叙事的纠偏，同时稳住徐明星本人信誉与 OKX 治理信心。"


def _cz_star_xu_player_secret_for_role(player_role: str) -> str:
    if player_role == "CZ":
        return "你知道只要拿不出足够硬的新证据，旧案一旦被深挖，回忆录就可能从武器反噬成自证偏见。"
    return "你知道反击越猛烈，外界越会重新翻出 2020 年提币暂停与旧合同证据，任何口误都会扩大成平台风险。"


def _cz_star_xu_opponent_for_role(player_role: str) -> str:
    if player_role == "CZ":
        return "徐明星/OKX 阵营的公开反击、会放大旧证据裂痕的围观者，以及把创始人口角映射成治理风险的市场情绪。"
    return "CZ 的回忆录叙事、高流量媒体转述、以及随时可能把旧案重新剪辑成你方治理原罪的行业围观者。"


def build_wuhan_university_yang_jingyuan_research_pack() -> MaterialResearchPack:
    official_notice = EvidenceNote(
        source_title=WHU_NOTICE_TITLE,
        source_url=WHU_NOTICE_URL,
        note=(
            "2025-09-20 校方通报：二审维持一审驳回杨某媛诉肖某瑫性骚扰损害纠纷请求，"
            "学校撤销肖某瑫记过处分，维持杨某媛硕士学位，并同步公布多项校内问责与辟谣结论。"
        ),
    )

    entity_cards = (
        EntityResearchCard(
            entity_id="whu-admin",
            name="武汉大学校方",
            role="校方",
            stance="强调依法依规复核并试图收束舆情外溢",
            public_position="尊重司法判决，撤销肖某瑫处分，维持杨景媛硕士学位，并对校内责任链启动问责整改。",
            conflict_stakes="核心风险是程序公信力、内部治理能力和持续舆论攻击的叠加损耗。",
            notable_pressures=("处分撤销后的公信力追问", "学位复核结论能否服众", "多部门被追责后的治理压力"),
            relationships=(
                ResearchRelationship("yang-jingyuan", "institutional-review", "对其论文、学位授予与相关传言进行复核并维持学位决定。"),
                ResearchRelationship("xiao-moutao", "discipline-reversal", "在司法节点后撤销对其记过处分，直接改变对位关系。"),
                ResearchRelationship("campus-public", "legitimacy-pressure", "需要同时面对校内外对于程序正当性和处置尺度的持续质疑。"),
            ),
            evidence=(official_notice,),
        ),
        EntityResearchCard(
            entity_id="yang-jingyuan",
            name="杨景媛",
            role="杨景媛",
            stance="维护个人学位与叙事合法性，但处在持续被审视的位置",
            public_position="其硕士学位经校内两阶段复核后被维持，校方称未发现抄袭、主观造假、篡改数据或编造结论。",
            conflict_stakes="核心利害是个人声誉、学位合法性与对外界质疑的承压能力。",
            notable_pressures=("论文存在百余处不规范问题", "网络传言叠加身份关系猜测", "与校方结论绑定后的被动性"),
            relationships=(
                ResearchRelationship("whu-admin", "dependent-conflict", "其学位与公开叙事高度依赖校方复核结论，同时也承受校方流程瑕疵外溢后果。"),
                ResearchRelationship("xiao-moutao", "direct-conflict", "与肖某瑫的纠纷是整个事件的原始冲突轴。"),
                ResearchRelationship("campus-public", "credibility-contest", "公众对其论文质量、背景传言和事件责任分配持续争执。"),
            ),
            evidence=(official_notice,),
        ),
        EntityResearchCard(
            entity_id="xiao-moutao",
            name="肖某瑫",
            role="肖某瑫",
            stance="借司法与校内复核节点获得翻盘空间",
            public_position="二审维持一审驳回杨某媛全部诉讼请求，校方随后撤销对其记过处分，并称其学业未中断。",
            conflict_stakes="核心利害是个人名誉、处分撤销后的叙事重建，以及是否继续承受公共争议余波。",
            notable_pressures=("仍被卷入长期舆论对冲", "围绕网暴与个人受损的传言反复扩散"),
            relationships=(
                ResearchRelationship("whu-admin", "vindication-via-review", "其局面改善依赖司法节点与校方复核结论。"),
                ResearchRelationship("yang-jingyuan", "direct-conflict", "与杨景媛之间的纠纷继续决定公众如何理解整个事件。"),
                ResearchRelationship("campus-public", "sympathy-volatility", "不同舆论群体会在同情、怀疑与反击之间快速切换。"),
            ),
            evidence=(official_notice,),
        ),
        EntityResearchCard(
            entity_id="econ-management-chain",
            name="经管学院与导师责任链",
            role="导师/学院体系",
            stance="进入防御整改状态，试图把问题限制在论文规范与培养流程层面",
            public_position="导师被约谈并暂停研究生招生资格两年，学院学位评定分委员会被责令检查整改。",
            conflict_stakes="核心利害是研究生培养责任、论文审核机制和学院治理信誉。",
            notable_pressures=("导师把关失守", "学院分委员会审核不严", "问责后制度修补压力"),
            relationships=(
                ResearchRelationship("yang-jingyuan", "training-chain", "其论文质量争议直接指向导师指导和学院审核责任。"),
                ResearchRelationship("whu-admin", "accountability", "校方问责将学院与导师链条直接纳入责任修复工程。"),
            ),
            evidence=(official_notice,),
        ),
        EntityResearchCard(
            entity_id="campus-public",
            name="校内外舆论与网络围观者",
            role="公众舆论",
            stance="围绕程序公正、论文质量与当事人遭遇持续撕裂",
            public_position="围绕优秀论文、修改论文、家庭背景、校友联名信及网暴后果等说法大量扩散，校方逐项辟谣。",
            conflict_stakes="核心利害是事件定义权——是程序纠偏、学术失范、舆论失真还是机构护短。",
            notable_pressures=("信息碎片化传播", "辟谣与再传播并存", "情绪化站队压缩细节讨论空间"),
            relationships=(
                ResearchRelationship("whu-admin", "trust-crisis", "对校方通报既是监督力量，也是持续施压来源。"),
                ResearchRelationship("yang-jingyuan", "credibility-pressure", "对其论文、背景与个人角色持续进行放大审视。"),
                ResearchRelationship("xiao-moutao", "reputation-whiplash", "会在受害、翻盘与反攻叙事之间快速切换。"),
            ),
            evidence=(official_notice,),
        ),
    )

    entities = (
        SeedEntity(
            id="whu-admin",
            name="武汉大学校方",
            role="校方",
            public_goal="稳住程序合法性与学校公信力",
            pressure_point="处分撤销和学位维持结论不被公众接受",
            starting_trust=32,
            influence=93,
            stance="高压止损",
            details="手握正式通报与问责权，但每一步都受外部舆论放大检视。",
        ),
        SeedEntity(
            id="yang-jingyuan",
            name="杨景媛",
            role="杨景媛",
            public_goal="保住学位与个人叙事合法性",
            pressure_point="论文不规范问题与背景传言持续发酵",
            starting_trust=28,
            influence=82,
            stance="被动自证",
            details="直接冲突当事人之一，其学位与个人名誉已被绑定到校方复核结论上。",
        ),
        SeedEntity(
            id="xiao-moutao",
            name="肖某瑫",
            role="肖某瑫",
            public_goal="巩固处分撤销后的名誉回升",
            pressure_point="任何新说法都可能把事件重新拉回旧叙事",
            starting_trust=41,
            influence=77,
            stance="翻盘反击",
            details="另一核心冲突当事人，司法节点和校方复核使其位置明显回升。",
        ),
        SeedEntity(
            id="econ-management-chain",
            name="经管学院与导师责任链",
            role="导师/学院体系",
            public_goal="把整改限制在制度修补层面",
            pressure_point="论文审核责任被继续深挖",
            starting_trust=24,
            influence=65,
            stance="防御整改",
            details="承接论文规范争议与培养责任问责，是校方体系内部的重要受压点。",
        ),
        SeedEntity(
            id="campus-public",
            name="校内外舆论与网络围观者",
            role="公众舆论",
            public_goal="逼出可被相信的完整解释",
            pressure_point="被不实信息和情绪化站队牵着走",
            starting_trust=18,
            influence=88,
            stance="高烈度撕裂",
            details="既推动追问，也是放大传言和惩罚性舆情的主要场域。",
        ),
    )

    disputes = (
        ResearchDispute(
            key="discipline-reversal",
            claim="对肖某瑫的纪律处分是否应被撤销",
            sides=("尊重司法判决与校方复核的一方", "质疑校方此前程序与现在纠偏尺度的一方"),
            status="contested",
        ),
        ResearchDispute(
            key="degree-integrity",
            claim="杨景媛论文虽未被认定学术不端，但在百余处不规范问题下是否仍应维持学位",
            sides=("主张学位维持的一方", "认为论文质量问题已足以动摇学位合法性的一方"),
            status="contested",
        ),
        ResearchDispute(
            key="rumor-boundary",
            claim="围绕背景关系、优秀论文、联名信和网暴后果的大量传言哪些属于事实",
            sides=("校方集中辟谣口径", "持续扩散未经核实说法的舆论人群"),
            status="active",
        ),
    )

    return MaterialResearchPack(
        case_id="wuhan-university-yang-jingyuan",
        title="武汉大学杨景媛事件",
        source_material=(
            "以武汉大学 2025-09-20《情况通报》为核心公开材料，整理处分撤销、二审判决、"
            "学位维持、导师/学院问责与网络传言清理的多线冲突结构。"
        ),
        premise="一份校方通报把司法结果、校内处分、学位复核、导师责任与舆情辟谣全部压到同一冲突面上。",
        opponent="对位当事人、持续撕裂的公众舆论与无法回避的程序公信力质疑",
        audience=("学生", "校友", "公众", "媒体观察者"),
        truth="这已不是单点指控，而是司法节点、校方复核、论文质量争议和网络传言同时争夺定义权的复合冲突。",
        entities=entities,
        candidate_viewpoints=("校方", "杨景媛"),
        opening_event=WorldEvent(
            headline="校方通报引爆二次舆论对冲",
            summary="处分撤销、学位维持与多项辟谣被同时抛出，直接把校方与杨景媛再次推到舆论核心。",
            severity=85,
            actor_id="whu-admin",
            actor_name="武汉大学校方",
        ),
        research_notes=(
            "当前研究包以武汉大学官方公开通报为核心证据源，适合作为第一版锚点世界的可审查基线。",
            "首批可玩角色限定为直接冲突双方中的校方与杨景媛；肖某瑫保留为高影响对位实体。",
            "论文质量争议、处分撤销争议与传言真假边界是后续冻结世界时必须保留的三条主冲突轴。",
        ),
        entity_cards=entity_cards,
        disputed_points=disputes,
    )


def build_wuhan_university_yang_jingyuan_frozen_world(*, player_role: str = "校方") -> FrozenInitialWorld:
    pack = build_wuhan_university_yang_jingyuan_research_pack()
    normalized_role = _normalize_wuhan_player_role(player_role)
    initial_dimensions = _wuhan_initial_dimensions_for_role(normalized_role)
    dimension_defs = _wuhan_dimension_defs()
    objective = _wuhan_objective_for_role(normalized_role)
    player_secret = _wuhan_player_secret_for_role(normalized_role)
    opponent = _wuhan_opponent_for_role(normalized_role)
    action_grammar = dimension_driven_world_action_grammar(
        initial_dimensions,
        dimension_defs,
        player_role=normalized_role,
        objective=objective,
    )

    return FrozenInitialWorld(
        world_id=f"{pack.case_id}-{'school' if normalized_role == '校方' else 'yang-jingyuan'}",
        title=pack.title,
        premise=pack.premise,
        player_role=normalized_role,
        player_secret=player_secret,
        objective=objective,
        opponent=opponent,
        audience=pack.audience,
        truth=pack.truth,
        selectable_roles=pack.candidate_viewpoints,
        allowed_turn_counts=(4, 6, 8, 10),
        opening_event=pack.opening_event,
        initial_dimensions=tuple(initial_dimensions.items()),
        entities=pack.entities,
        ending_bands=_wuhan_ending_bands(),
        dimension_defs=dimension_defs,
        action_grammar=action_grammar,
        reaction_boundaries=default_agent_reaction_boundaries(),
    )


def _normalize_wuhan_player_role(player_role: str) -> str:
    normalized = player_role.strip()
    if normalized not in {"校方", "杨景媛"}:
        raise ValueError(f"Unsupported Wuhan anchor role: {player_role}")
    return normalized


def _wuhan_initial_dimensions_for_role(player_role: str) -> dict[str, int]:
    by_role = {
        "校方": {
            "credibility": 36,
            "treasury": 61,
            "pressure": 68,
            "price": 50,
            "liquidity": 53,
            "sell_pressure": 57,
            "volatility": 62,
            "community_panic": 74,
            "rumor_level": 71,
            "narrative_control": 34,
            "exchange_trust": 39,
            "control": 72,
        },
        "杨景媛": {
            "credibility": 24,
            "treasury": 42,
            "pressure": 87,
            "price": 50,
            "liquidity": 47,
            "sell_pressure": 66,
            "volatility": 69,
            "community_panic": 82,
            "rumor_level": 76,
            "narrative_control": 46,
            "exchange_trust": 28,
            "control": 45,
        },
    }
    return dict(by_role[player_role])


def _wuhan_dimension_defs() -> tuple[WorldDimensionDef, ...]:
    return (
        WorldDimensionDef("credibility", "公信力", "玩家阵营能否让外界相信自己的程序和说法。", "higher_is_better", 55, 35, 20),
        WorldDimensionDef("treasury", "协调余量", "还能调动多少制度、关系与执行资源去灭火。", "higher_is_better", 45, 25, 10),
        WorldDimensionDef("pressure", "承压值", "来自舆论、程序与对位方的即时压强。", "lower_is_better", 55, 75, 90),
        WorldDimensionDef("price", "议题温度", "事件是否仍在高位占据公共注意力。", "lower_is_better", 55, 70, 85),
        WorldDimensionDef("liquidity", "回旋空间", "是否还有足够空间调整叙事和处置动作。", "higher_is_better", 50, 30, 15),
        WorldDimensionDef("sell_pressure", "追责势能", "要求继续深挖和继续追责的势能。", "lower_is_better", 45, 65, 80),
        WorldDimensionDef("volatility", "舆情波动", "叙事是否持续在新爆点和旧传言间抽搐。", "lower_is_better", 45, 65, 80),
        WorldDimensionDef("community_panic", "群体撕裂", "校内外相关人群的情绪是否继续分裂升级。", "lower_is_better", 45, 65, 80),
        WorldDimensionDef("rumor_level", "传言强度", "未经核实说法扩散和反复再传播的强度。", "lower_is_better", 40, 60, 75),
        WorldDimensionDef("narrative_control", "叙事控制", "玩家阵营是否还能主导事件定义。", "higher_is_better", 55, 35, 20),
        WorldDimensionDef("exchange_trust", "程序信任", "外界对复核、问责和解释程序的信任程度。", "higher_is_better", 55, 35, 20),
        WorldDimensionDef("control", "控制权", "玩家阵营对事态节奏和后续动作的掌控程度。", "higher_is_better", 60, 35, 20),
    )


def _wuhan_ending_bands() -> tuple[WorldEndingBand, ...]:
    return (
        WorldEndingBand(80, "wuhan-procedure-anchored", "程序定锚", "你把司法、问责与复核叙事重新钉回可解释框架，局面暂时稳住。"),
        WorldEndingBand(55, "wuhan-contested-drift", "争议拖行", "你避免了立刻失控，但冲突继续拖行，任何新材料都可能再次引爆。"),
        WorldEndingBand(30, "wuhan-accountability-fracture", "问责失序", "程序修复没有止住追责外溢，越来越多人开始把事件理解为系统性失守。"),
        WorldEndingBand(0, "wuhan-trust-void", "信任坠空", "叙事、防线与程序信任同时坠落，世界滑向长期失控。"),
    )


def _wuhan_objective_for_role(player_role: str) -> str:
    if player_role == "校方":
        return "在多线质疑中重新稳住程序公信力，并防止事件继续升级成整体治理失信。"
    return "在被动承压中保住个人学位与叙事合法性，并避免再次被全面定义为事件替罪羊。"


def _wuhan_player_secret_for_role(player_role: str) -> str:
    if player_role == "校方":
        return "你知道校内流程漏洞比公开通报写得更深，任何额外细节外泄都会把问责从个案拉成系统性质疑。"
    return "你知道自己的学位与名誉高度绑定在校方复核结论上，一旦程序公信力继续下坠，你几乎没有独立防线。"


def _wuhan_opponent_for_role(player_role: str) -> str:
    if player_role == "校方":
        return "杨景媛一侧的个人叙事防守、持续撕裂的公众舆论，以及对学校程序正当性的追问。"
    return "校方主导的程序叙事、肖某瑫翻盘后的对位压力，以及持续发酵的公众审视。"
