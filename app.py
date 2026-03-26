import os
from datetime import datetime

import anthropic
import streamlit as st

# ─── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI产品力内容生产",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stTextArea textarea { font-size: 14px; }
    .copy-box { background: #f6f8fa; border-radius: 8px; padding: 12px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─── Session state ───────────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []

# ─── Helpers ────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """你是一个专业的内容创作专家，精通各类平台的文案写作风格，包括：小红书、微博、朋友圈、公众号，以及 moomoo 投资社区（英文金融内容）。

你的仿写能力体现在：
• 精准识别：语气、节奏、句式长短、段落结构
• 手法复现：排比、反问、emoji 使用习惯、标点风格
• 平台适配：理解不同平台的内容规律和用户习惯
• 创意独立：风格相似，内容 100% 原创，绝不重复示例

黄金法则：形神兼备，内容全新。

【语言规则】默认使用英文输出。仅当平台规范、示例文案或用户要求中明确指定中文时，才使用中文。"""

# Platform-specific style guidance injected into the prompt
PLATFORM_STYLE_MAP = {
    "moomoo社区": """
【moomoo 社区平台风格规范】
moomoo 是面向全球散户的投资交易平台，社区内容以英文为主，主要涵盖市场资讯、交易技巧、平台功能介绍。

核心风格特征：
1. 开篇称呼：固定以 "Dear mooers," 开场，建立社区归属感
2. 语气：专业友好（professional yet approachable），像老练的投资者在向社区朋友分享
3. 结构逻辑：痛点/场景导入 → 解决方案/功能介绍 → 操作步骤（① ② ③）→ 社区互动 CTA（留评有礼、积分奖励）
4. Emoji 使用：金融/科技相关 emoji 适度点缀，如 📈 📉 💡 ✅ 🎉 🔥 💰，不过度堆砌
5. 段落：短段（3-5 行），使用加粗标题分层，重要术语加粗
6. 专业术语：金融英文术语正常使用，必要时括号补注（如 Trailing Stop Order）
7. 结尾固定元素：
   - 互动邀请（如 "Comment below to share your experience and win up to X points!"）
   - 风险免责声明（一句话："Investments involve risk. Please trade responsibly."）
8. 平台特色：可自然提及 moomoo 的功能优势（zero commission、real-time data 等），但不硬广
9. 语言：全文英文（或以英文为主）
""",

    "Reddit": """
【Reddit 平台风格规范】
Reddit 是高度社区驱动的论坛平台，投资相关内容主要发布在 r/investing、r/options、r/stocks、r/moomoo 等子版块。Reddit 用户对营销内容极度敏感，任何硬广或过度宣传都会被下沉甚至举报。

核心风格特征：
1. 语气：真实、坦诚、去中心化，像一个有经验的散户在分享自己的真实观点或研究
2. 内容结构：
   - 标题：具体、有信息量，能独立传递核心观点（例："How I use Expected Move to size my options positions"）
   - 正文：开门见山，数据/案例优先，避免空话
   - 结尾：可加 TL;DR（太长不看）总结，1-3 行
3. 格式：善用 Markdown（## 标题、**加粗**、> 引用、- 列表），长帖要有层级感
4. Emoji：极少使用，偶尔一两个即可，过多显得不成熟
5. 禁忌：
   - 绝对不能出现明显的广告语气或"立即下载/注册"等 CTA
   - 不能夸大收益或保证回报
   - 如提及平台/工具，需以"我用的是 XXX"等第一人称经验方式带出，不能直接推介
6. 互动：结尾可抛出一个问题引发讨论（"What's your go-to strategy for earnings plays?"）
7. 语言：全文英文
""",

    "X": """
【X（原 Twitter）平台风格规范】
X 是快节奏、注意力稀缺的平台，金融内容（FinTwit）圈子活跃。内容要在 0.5 秒内抓住眼球，观点要鲜明，语言要简洁有力。

核心风格特征：
1. 单条推文：≤ 280 字符，首句即核心——必须是 hook，让人停下来
2. 串推（Thread）：适合稍长内容，格式为 "1/" "2/" "3/" ... 结尾用"— END —"或总结句收尾
3. 语气：自信、直接、有态度，像 FinTwit 上的 KOL 在发表市场观点
4. 内容节奏：短句 > 长句，能用数字就用数字（"82% of retail traders lose on earnings week"）
5. Emoji：战略性使用，每条 1-3 个即可，常用：📊 📈 🔥 💡 ⚡ 🧵（表示有 thread）
6. Hashtags：2-3 个精准标签，如 #options #investing #FinTwit #stocks，不堆砌
7. 结构（Thread 示例）：
   - Tweet 1：强 hook / 反常识观点 / 数据震撼
   - Tweet 2-N：展开论据、步骤、案例
   - 最后一条：总结 + CTA（"Follow for more" / "RT if this helped"）
8. 禁忌：不用被动语态，不说废话，不写超过两行的长句
9. 语言：全文英文
""",
}

# TA profile injected into the prompt to guide audience-specific messaging
TA_PROFILE_MAP = {
    "熟手（中高风险偏好）": """
【目标客群画像：熟手（中高风险偏好）——P0 级核心创收主力】
年龄：25-42 岁
特征：进阶交易者，交易频次高、期权渗透率深，部分将交易作为副业。紧盯 CPI、财报等宏观事件，具备成熟的自主交易逻辑。ARPU 极高。

核心痛点："看得到机会，却受制于工具"
- 轻量级平台（如 Robinhood、Webull）无法支撑复杂期权策略和组合风控
- 极端波动时，平台决策支持弱、执行速度慢，常错失最佳价格

moomoo 对这类用户的核心价值主张："你不是不敢交易，你是缺一个更专业的工具"
关键卖点：专业级期权链、可视化策略构建器（Strategy Builder）、Level 2/IV/Expected Move 进阶深度数据、移动端 Pro Tools、AI Agent API、极速执行。
沟通方向：强调工具的专业度、执行速度和掌控感，让他们感受到"降维打击"式的交易效率提升。
""",

    "华人": """
【目标客群画像：华人客群——P0 级高净值基本盘】
年龄：28-50 岁
特征：资产体量大，对专业工具接受度高，极度重视信息获取效率、账户安全和资金安全。AUM 高，有资产配置需求，社群口碑传播能力极强。

核心痛点："信息获取与工具门槛的错位"
- 习惯信息密度大、可自定义的模块化工具，但市面期权/组合工具门槛太高
- 外资平台在税务处理、账户安全感和文化认同上存在隔阂

moomoo 对这类用户的核心价值主张："专业但不难懂，华人用得放心"
关键卖点：期权链、条件单等顶级专业工具 + 7×24 小时全天候中文专属服务 + Cash Sweep 闲钱理财 + 美股 IPO / 财报等赚钱效应抓手。
沟通方向：强调安全感、中文服务、一站式便利，打通"研究-交易-资产沉淀"闭环，消除文化/语言隔阂。
""",

    "熟手（中低风险偏好）": """
【目标客群画像：熟手（中低风险偏好）——P1 级长期资产压舱石】
年龄：30-55 岁
特征：专业人士或企业主，"研究后下单"型理性投资者。看重长线回报、税务优化和资产传承，持有 IRA/401k 账户。AUM 极高，交易频次偏低，是平台长期留存与资产沉淀的压舱石。

核心痛点："决策成本太高"
- 想做精细化风控和研究，但工具太分散（需在多个 App 间来回切换）
- 现有工具要么太浅薄（如 Robinhood），要么风控展示极不直观

moomoo 对这类用户的核心价值主张："更稳、更清楚、更省脑力"
关键卖点：一站式整合 Yahoo Finance + TradingView + Seeking Alpha 的分析能力、Smart Money 追踪主力资金、Cash Sweep 稳健理财、Moomoo AI 智能辅助。
沟通方向：强调省时省力、全局掌控、决策清晰，帮忙工作繁忙时也能轻松管理财富。
""",
}

TONE_MAP = {
    "保持原样": "与示例保持一致",
    "活泼有趣": "活泼、俏皮、充满活力",
    "真诚温暖": "真诚、温暖、感性细腻",
    "专业干货": "专业、理性、有说服力",
    "幽默搞笑": "幽默、搞笑、接地气",
}

LENGTH_MAP = {
    "保持原样": "篇幅与示例相近",
    "短（100 字以内）": "控制在 100 字以内，精炼",
    "中（200-400 字）": "200-400 字，详略得当",
    "长（400 字以上）": "400 字以上，内容丰富充实",
}


def build_user_message(examples: list[str], requirements: str, platform: str, tone: str, length: str, ta: str = "") -> str:
    has_examples = any(e.strip() for e in examples)

    # Inject platform-specific style guide when available
    platform_guide = PLATFORM_STYLE_MAP.get(platform, "")
    platform_guide_section = f"\n{platform_guide}\n" if platform_guide else ""

    ta_line = f"👥 目标客群（TA）：{ta}\n" if ta else ""
    ta_profile = TA_PROFILE_MAP.get(ta, "")
    ta_section = f"\n{ta_profile}\n" if ta_profile else ""

    if has_examples:
        examples_block = ""
        for i, ex in enumerate(examples, 1):
            if ex.strip():
                examples_block += f"\n---【示例 {i}】---\n{ex.strip()}\n"

        task_intro = "请分析以下示例文案的写作风格，然后根据要求进行仿写。"
        examples_section = f"""
===【示例文案】===
{examples_block}"""
        output_format = """**📊 风格分析**
（提炼 3 个最核心的风格特征，每条一行）

---

**✨ 仿写结果**
（直接输出正文内容，不加任何说明。注意：此标题行必须原样保留，内容语言按平台规范输出）"""
    else:
        task_intro = "没有示例文案，请根据平台规范、目标客群画像和内容需求，凭借你对该平台的深度理解直接创作一篇高质量内容。"
        examples_section = ""
        output_format = """**✨ 仿写结果**
（直接输出正文内容，不加任何说明。注意：此标题行必须原样保留，内容语言按平台规范输出）"""

    return f"""{task_intro}
{platform_guide_section}{ta_section}{examples_section}
===【内容需求】===
📱 发布平台：{platform}
{ta_line}📋 内容主题 / 要求：{requirements}
🎨 语气风格：{TONE_MAP.get(tone, tone)}
📏 字数参考：{LENGTH_MAP.get(length, length)}

===【输出格式】===
请严格按以下格式输出，不要省略任何部分：

{output_format}"""


def stream_content(api_key: str, examples: list[str], requirements: str, platform: str, tone: str, length: str, ta: str = ""):
    """Yield text tokens from Claude streaming response."""
    client = anthropic.Anthropic(
        api_key=api_key,
        base_url="https://llm-proxy.futuoa.com",
        default_headers={"Authorization": f"Bearer {api_key}"},
    )
    user_message = build_user_message(examples, requirements, platform, tone, length, ta)

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=8000,
        thinking={"type": "enabled", "budget_tokens": 3000},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        for text in stream.text_stream:
            yield text


def extract_result(full_text: str) -> str:
    """Extract only the 仿写结果 section for easy copying."""
    for marker in ["仿写结果", "生产结果", "Imitation Result", "Generated Content", "Result"]:
        if marker in full_text:
            after = full_text.split(marker, 1)[1]
            return after.lstrip("*\n —-").strip()
    # Fallback: if no marker found, strip any style analysis section before "---"
    if "\n---\n" in full_text:
        return full_text.split("\n---\n", 1)[1].strip()
    return full_text.strip()


# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 配置")

    api_key = st.text_input(
        "Anthropic API Key",
        value=os.environ.get("ANTHROPIC_API_KEY", ""),
        type="password",
        help="从 console.anthropic.com 获取",
    )
    if api_key:
        st.success("✅ API Key 已设置")
    else:
        st.warning("请输入 API Key 后使用")

    st.divider()
    st.header("📐 生成参数")

    ta = st.selectbox(
        "TA（目标客群）",
        ["熟手（中低风险偏好）", "熟手（中高风险偏好）", "华人"],
        help="选择目标受众，AI 会调整内容的侧重点和沟通方式",
    )

    platform = st.selectbox(
        "发布平台",
        ["moomoo社区", "小红书", "Reddit", "X", "通用文案"],
        help="AI 会根据平台调性调整语气、结构和格式",
    )
    tone = st.selectbox(
        "语气调整",
        list(TONE_MAP.keys()),
        help="在原有风格基础上微调语气",
    )
    length = st.selectbox("字数参考", list(LENGTH_MAP.keys()))

    st.divider()
    st.caption(f"已生成 {len(st.session_state.history)} 条记录")
    if st.session_state.history and st.button("🗑️ 清空历史", use_container_width=True):
        st.session_state.history = []
        st.rerun()

# ─── Main tabs ───────────────────────────────────────────────────────────────
tab_write, tab_history = st.tabs(["✍️ 内容生产", "📚 历史记录"])

with tab_write:
    st.title("✍️ AI产品力内容生产")
    st.caption("给我示例文案 + 你的要求，AI 帮你生成新内容")

    col_left, col_right = st.columns([1.1, 0.9], gap="large")

    with col_left:
        st.subheader("📝 示例文案（可选）")
        st.caption("粘贴 1-3 篇风格参考，越多越准确；不填则 AI 按平台 & TA 理解直接创作")

        example1 = st.text_area(
            "示例 1 *",
            height=150,
            placeholder="粘贴你最喜欢、风格最典型的一篇参考文案...",
            key="ex1",
        )
        example2 = st.text_area(
            "示例 2（可选）",
            height=110,
            placeholder="再粘贴一篇，帮 AI 更好理解你的风格偏好",
            key="ex2",
        )
        example3 = st.text_area(
            "示例 3（可选）",
            height=110,
            placeholder="第三篇示例（可选）",
            key="ex3",
        )

    with col_right:
        st.subheader("🎯 内容需求")
        st.caption("描述你想创作的内容")

        placeholder_map = {
            "moomoo社区": (
                "Topic: Introduce moomoo's Earnings Hub feature\n"
                "Key info: AI summaries, volatility analysis, peer benchmarking\n"
                "CTA: Comment to win up to 1,000 points\n"
                "Tone: Professional but friendly"
            ),
            "小红书": (
                "主题：分享我用 moomoo 做期权交易的心得\n"
                "关键信息：操作简单、数据全、有 AI 辅助\n"
                "目标读者：想入门期权的年轻投资者\n"
                "其他：真实感强，带个人经历"
            ),
            "Reddit": (
                "Topic: Share a trading strategy or platform experience\n"
                "Key info: Specific data, personal experience, honest pros/cons\n"
                "Subreddit: r/options or r/investing\n"
                "Tone: Authentic, community-first, no hard sell"
            ),
            "X": (
                "Topic: A sharp market insight or trading tip (thread or single tweet)\n"
                "Key info: One strong hook + supporting points\n"
                "Format: Thread (1/N) or single punchy tweet\n"
                "Tone: Confident, direct, FinTwit style"
            ),
            "通用文案": (
                "描述你的内容主题和关键信息即可，AI 会生成通用风格的文案。\n\n"
                "例如：介绍 moomoo 的 Cash Sweep 功能，强调闲钱自动生息、随时可取"
            ),
        }
        requirements = st.text_area(
            "内容要求 *",
            height=220,
            placeholder=placeholder_map.get(platform, "描述你的内容主题和关键信息..."),
            key="req",
        )

        st.divider()
        generate_btn = st.button("🚀 开始生产", type="primary", use_container_width=True)

    # ── Output ──────────────────────────────────────────────────────────────
    st.divider()

    if generate_btn:
        examples = [example1 or "", example2 or "", example3 or ""]

        # Validation
        if not api_key:
            st.error("⚠️ 请在左侧边栏输入 Anthropic API Key")
            st.stop()
        if not requirements.strip():
            st.error("⚠️ 请填写内容需求")
            st.stop()

        st.subheader("✨ 生产结果")
        status = st.empty()
        status.info("🤔 AI 正在分析风格，请稍候…")

        try:
            result = st.write_stream(
                stream_content(api_key, examples, requirements, platform, tone, length, ta)
            )
            status.empty()
            st.success("✅ 内容生产完成！")

            # Copyable result section
            with st.expander("📋 点击展开 / 复制生产结果"):
                copy_text = extract_result(result)
                st.code(copy_text, language=None)
                st.caption("点击右上角的复制图标即可复制")

            # Save to history
            st.session_state.history.insert(0, {
                "time": datetime.now().strftime("%m-%d %H:%M"),
                "platform": platform,
                "ta": ta,
                "tone": tone,
                "requirements": requirements[:60] + ("…" if len(requirements) > 60 else ""),
                "full_result": result,
                "copy_text": copy_text,
                "examples_count": sum(1 for e in examples if e.strip()),
            })

        except anthropic.AuthenticationError:
            status.empty()
            st.error("❌ API Key 无效，请检查密钥是否正确")
        except anthropic.RateLimitError:
            status.empty()
            st.error("❌ 请求频率过高，请稍等片刻再试")
        except anthropic.BadRequestError as e:
            status.empty()
            st.error(f"❌ 请求参数有误：{e.message}")
        except Exception as e:
            status.empty()
            st.error(f"❌ 发生错误：{e}")

    elif not any([example1, example2, example3, requirements]):
        st.info("👆 在上方填写示例文案和内容需求，然后点击「开始生产」")

# ─── History tab ─────────────────────────────────────────────────────────────
with tab_history:
    if not st.session_state.history:
        st.info("暂无历史记录。完成内容生产后会自动保存到这里。")
    else:
        for item in st.session_state.history:
            label = f"[{item['time']}]  {item['platform']} · {item.get('ta', '')} · {item['tone']}  |  {item['requirements']}"
            with st.expander(label):
                st.markdown(item["full_result"])
                st.divider()
                st.caption("📋 仅生产结果（便于复制）")
                st.code(item["copy_text"], language=None)
                st.caption(f"使用了 {item['examples_count']} 篇示例")
