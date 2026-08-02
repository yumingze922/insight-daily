"""
每日深度思辨 —— 每日自动更新脚本

功能：
1. 从36氪「八点一氪」获取今日新闻摘要
2. 调用LLM选出最值得深度分析的事件（3条不同主题）
3. 调用LLM生成多学科多维度分析
4. 将结果存入 public/data/today.json（供PWA读取）
5. 通过飞书/企业微信机器人推送通知

运行方式：
  python scripts/daily_update.py

环境变量：
  DEEPSEEK_API_KEY  - DeepSeek API Key（必需）
  FEISHU_WEBHOOK    - 飞书自定义机器人 Webhook URL（可选）
  WECOM_WEBHOOK     - 企业微信机器人 Webhook URL（可选）
  DINGTALK_WEBHOOK  - 钉钉机器人 Webhook URL（可选）
"""

import json
import os
import sys
import re
import time
import base64
from datetime import datetime
from pathlib import Path
from typing import Optional

# Windows 控制台默认 GBK 编码，无法输出 emoji，强制使用 UTF-8
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import httpx


# ============================================================
# 签名工具
# ============================================================

def generate_feishu_sign(timestamp: str, secret: str) -> str:
    """飞书自定义机器人签名：HMAC-SHA256(key=ts+\n+secret, msg='') → base64"""
    import hashlib
    import hmac as hmac_lib
    key = (timestamp + '\n' + secret).encode('utf-8')
    msg = ''.encode('utf-8')
    h = hmac_lib.new(key, msg, hashlib.sha256)
    return base64.b64encode(h.digest()).decode('utf-8')


# ============================================================
# 配置
# ============================================================

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# 推送渠道（至少配置一个）
PUSH_CHANNELS = {
    "feishu": os.environ.get("FEISHU_WEBHOOK", ""),
    "wecom": os.environ.get("WECOM_WEBHOOK", ""),
    "dingtalk": os.environ.get("DINGTALK_WEBHOOK", ""),
}
FEISHU_SECRET = os.environ.get("FEISHU_SECRET", "")

# 输出路径
OUTPUT_DIR = Path(__file__).parent.parent / "public" / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# DeepSeek System Prompt（从 backend/prompts.py 导入的逻辑）
EVENT_SELECTION_PROMPT = """你是一位时事观察者。以下是今日36氪「八点一氪」的新闻摘要。

请从中选出3条最值得深度分析的事件（每条代表不同的主题方向）：

- 第1条：跨领域重大事件（科技/地缘/经济/社会）
- 第2条：互联网行业动态（平台变化/竞争格局/用户行为）
- 第3条：AI产品经理趋势思辨（角色进化/能力模型/行业周期）

对每条事件输出：
1. 标题（20字以内，有张力）
2. 摘要（80字以内，抓住核心矛盾）
3. 影响评级（1-5星）
4. 标签（2-3个关键词）

请直接以JSON数组格式输出，不要有其他文字。

今日新闻摘要：
{news_summaries}"""

ANALYSIS_PROMPT = """你是一位跨学科分析师。请针对以下事件生成深度分析。

## 事件
{event}

## 分析结构（JSON格式输出）

{{
  "overview": {{
    "what": "发生了什么（30字）",
    "who": "涉及哪些主体（30字）",
    "when": "时间节点",
    "where": "影响范围",
    "why": "深层动因（40字）",
    "how": "路径方式（30字）",
    "keyData": "关键数据",
    "fullSummary": "完整概述（150字）"
  }},
  "viewpoints": [
    {{"stance": "optimistic", "stanceLabel": "乐观派", "source": "来源", "text": "分析（120字）"}},
    {{"stance": "cautious", "stanceLabel": "谨慎派", "source": "来源", "text": "分析（120字）"}},
    {{"stance": "critical", "stanceLabel": "批判派", "source": "来源", "text": "分析（120字）"}},
    {{"stance": "industry", "stanceLabel": "行业视角", "source": "来源", "text": "分析（120字）"}}
  ],
  "perspectives": [
    {{
      "discipline": "学科名称",
      "theory": "理论/学者名称",
      "quote": "核心引用（典籍原文或理论金句）",
      "source": "出处",
      "icon": "单字标识",
      "text": "分析（120字）"
    }}
  ],
  "insight": {{
    "text": "核心独到观点（80字）",
    "framework": {{
      "title": "分析框架名称",
      "content": "框架逻辑层次（120字）"
    }}
  }},
  "dialogue": {{
    "phases": [
      {{"phase": 1, "name": "设问", "messages": [{{"role": "system", "text": "开场问题", "classical": null}}]}},
      {{"phase": 2, "name": "追问", "messages": [{{"role": "system", "text": "追问", "classical": null}}]}},
      {{"phase": 3, "name": "多学科碰撞", "messages": [{{"role": "system", "text": "多学科问题", "classical": {{"quote": "...", "source": "..."}}}}]}},
      {{"phase": 4, "name": "独见注入", "messages": [{{"role": "system", "text": "独到见解", "classical": null}}]}},
      {{"phase": 5, "name": "总结", "messages": [{{"role": "system", "text": "总结语", "classical": null}}]}}
    ],
    "note": {{
      "coreProposition": "核心命题",
      "mainstreamView": "主流观点总结",
      "alternativeView": "另类视角",
      "multidisciplinaryInsight": "多学科洞察",
      "personalJudgment": "综合判断",
      "actionTakeaway": "行动启示"
    }}
  }}
}}

要求：
- perspectives 至少3个（从华夏典籍、经济学、管理学、心理学、政治学、社会学中选取最相关的）
- 观点要有深度和原创性，不要空洞
- 直接输出JSON，不要有其他文字"""


# ============================================================
# LLM 调用
# ============================================================

async def call_llm(system_prompt: str, user_message: str) -> str:
    """调用 DeepSeek API"""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("未设置 DEEPSEEK_API_KEY 环境变量")

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "max_tokens": 4096,
        "temperature": 0.7
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{DEEPSEEK_BASE}/v1/chat/completions",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


def extract_json(text: str) -> dict:
    """从 LLM 返回的文字中提取 JSON"""
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试提取 ```json ... ``` 代码块
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试提取 { ... } 或 [ ... ]
    for pattern in [r'\[.*\]', r'\{.*\}']:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                continue

    raise ValueError(f"无法从LLM输出中提取JSON:\n{text[:500]}")


# ============================================================
# 36氪新闻获取（RSS Feed）
# ============================================================

async def fetch_36kr_news() -> str:
    """从36氪 RSS Feed 获取今日「八点一氪」新闻摘要

    数据源：https://36kr.com/feed
    每天早上 7:48 左右发布，我们的 cron 在 8:00 触发，时间刚好。

    返回：八点一氪专栏的标题 + 正文内容（纯文本）
    """
    import re
    import xml.etree.ElementTree as ET

    print("   尝试从 36kr RSS Feed 获取...")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://36kr.com/feed",
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; InsightDaily/1.0)"
                }
            )
            resp.raise_for_status()
            xml_text = resp.text

            if not xml_text or len(xml_text) < 100:
                raise ValueError("RSS 返回空内容")

            # 解析 XML，找到「八点一氪」文章
            items = re.findall(r'<item>(.*?)</item>', xml_text, re.DOTALL)

            for item_xml in items:
                title_match = re.search(r'<title>(.*?)</title>', item_xml)
                desc_match = re.search(
                    r'<description><!\[CDATA\[(.*?)\]\]></description>',
                    item_xml, re.DOTALL
                )
                link_match = re.search(r'<link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>', item_xml)

                if not title_match:
                    continue

                title = title_match.group(1)

                # 匹配「8点1氪」或「八点一氪」
                if '8点1氪' in title or '八点一氪' in title:
                    content = ""
                    if desc_match:
                        # 去除 HTML 标签，保留纯文本
                        content = re.sub(r'<[^>]+>', '', desc_match.group(1))
                        content = re.sub(r'\s+', ' ', content).strip()

                    article_url = link_match.group(1) if link_match else ""

                    result = f"【今日八点一氪】\n标题：{title}\n\n正文摘要：\n{content[:3000]}"
                    if article_url:
                        result += f"\n\n原文链接：{article_url}"

                    print(f"   ✅ 成功获取「八点一氪」(标题: {title[:50]}...)")
                    print(f"   内容长度: {len(content)} 字符")

                    return result

            # 如果没找到八点一氪（比如周末不更新），回退：取 RSS 前5篇文章标题
            print("   ⚠️  未找到「八点一氪」专栏，回退到最新文章列表")
            all_titles = re.findall(r'<title>(.*?)</title>', xml_text)
            # 跳过第一个（channel title）
            news_titles = [t for t in all_titles[1:6] if t.strip()]
            if news_titles:
                fallback = "【今日36氪要闻】（八点一氪未更新，以下为最新文章列表）\n\n"
                for i, t in enumerate(news_titles, 1):
                    fallback += f"{i}. {t}\n"
                print(f"   回退获取到 {len(news_titles)} 篇文章标题")
                return fallback

            raise ValueError("RSS Feed 中无可用内容")

    except Exception as e:
        print(f"   ❌ RSS 获取失败: {e}")

        # 终极回退：手动输入文件
        input_file = Path(__file__).parent / "news_input.txt"
        if input_file.exists():
            content = input_file.read_text(encoding="utf-8").strip()
            if content:
                print(f"   使用本地 news_input.txt ({len(content)} 字符)")
                return content

        raise RuntimeError(
            "所有新闻源均不可用。请检查：\n"
            "1. 网络是否可访问 36kr.com\n"
            "2. 或创建 scripts/news_input.txt 手动粘贴今日摘要"
        )


# ============================================================
# 推送通知
# ============================================================

async def push_notification(event_title: str, event_summary: str, event_id: str, base_url: str):
    """向配置的IM平台推送通知"""
    analysis_url = f"{base_url}?event={event_id}"

    # 飞书推送
    if PUSH_CHANNELS["feishu"]:
        await push_feishu(event_title, event_summary, analysis_url)

    # 企业微信推送
    if PUSH_CHANNELS["wecom"]:
        await push_wecom(event_title, event_summary, analysis_url)

    # 钉钉推送
    if PUSH_CHANNELS["dingtalk"]:
        await push_dingtalk(event_title, event_summary, analysis_url)

    if not any(PUSH_CHANNELS.values()):
        print("⚠️  未配置任何推送渠道（FEISHU_WEBHOOK / WECOM_WEBHOOK / DINGTALK_WEBHOOK）")


async def push_feishu(title: str, summary: str, url: str):
    """飞书自定义机器人 —— 富文本卡片消息（带签名校验）"""
    ts = str(int(time.time()))

    payload = {
        "timestamp": ts,
        "sign": generate_feishu_sign(ts, FEISHU_SECRET) if FEISHU_SECRET else "",
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": "每日深度思辨"},
                "template": "wathet"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**{title}**\n\n{summary[:120]}..."
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "开始今日思辨"},
                            "type": "primary",
                            "url": url
                        }
                    ]
                }
            ]
        }
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(PUSH_CHANNELS["feishu"], json=payload)
        if resp.status_code == 200 and resp.json().get("code") == 0:
            print("✅ 飞书推送成功")
        else:
            print(f"❌ 飞书推送失败: {resp.status_code} {resp.text}")


async def push_wecom(title: str, summary: str, url: str):
    """企业微信机器人 —— Markdown 消息"""
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": (
                f"## 每日深度思辨\n"
                f"**{title}**\n\n"
                f">{summary[:150]}...\n\n"
                f"[开始今日思辨]({url})"
            )
        }
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(PUSH_CHANNELS["wecom"], json=payload)
        if resp.status_code == 200:
            print("✅ 企业微信推送成功")
        else:
            print(f"❌ 企业微信推送失败: {resp.status_code} {resp.text}")


async def push_dingtalk(title: str, summary: str, url: str):
    """钉钉机器人 —— ActionCard 消息"""
    payload = {
        "msgtype": "actionCard",
        "actionCard": {
            "title": "每日深度思辨",
            "text": f"### {title}\n\n{summary[:200]}...",
            "btnOrientation": "0",
            "singleTitle": "开始今日思辨",
            "singleURL": url
        }
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(PUSH_CHANNELS["dingtalk"], json=payload)
        if resp.status_code == 200:
            print("✅ 钉钉推送成功")
        else:
            print(f"❌ 钉钉推送失败: {resp.status_code} {resp.text}")


# ============================================================
# 主流程
# ============================================================

async def main():
    print("=" * 60)
    print("  每日深度思辨 · 自动更新")
    print(f"  执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # PWA 部署地址（手机可访问的公网地址）
    base_url = os.environ.get("BASE_URL", "https://1bb5b1f19fe64920b4aff8618fd1c1a0.sh3.agentos-app.net")
    
    # 支持通过命令行 --date YYYY-MM-DD 或环境变量 DATE_OVERRIDE 指定日期
    target_date = os.environ.get("DATE_OVERRIDE", None)
    if not target_date and "--date" in sys.argv:
        idx = sys.argv.index("--date")
        if idx + 1 < len(sys.argv):
            target_date = sys.argv[idx + 1]
    if target_date:
        today = target_date
    else:
        today = datetime.now().strftime("%Y-%m-%d")

    display_date = datetime.strptime(today, "%Y-%m-%d" if "-" in today else "%Y%m%d").strftime("%Y年%m月%d日")

    # 防重复保险：如果当天数据已生成过，直接跳过（避免云上+本地双重触发导致重复推送）
    existing_file = OUTPUT_DIR / f"{today}.json"
    if existing_file.exists():
        try:
            existing = json.loads(existing_file.read_text(encoding="utf-8"))
            gen_date = existing.get("generated_at", "")[:10]
            if gen_date == today:
                print(f"⚠️  当天数据已存在（{gen_date}），跳过本次生成，避免重复推送。")
                print(f"   如需强制重新生成，请删除 {existing_file} 后再运行。")
                return
        except json.JSONDecodeError:
            pass

    # 1. 获取新闻
    print("\n📰 正在获取今日新闻...")
    news_text = await fetch_36kr_news()
    print(f"   获取到 {len(news_text)} 字符")

    # 2. LLM 精选事件
    print("\n🤖 LLM 正在精选事件...")
    selection_result = await call_llm(
        EVENT_SELECTION_PROMPT.format(news_summaries=news_text[:3000]),
        "请按要求选出3条事件并输出JSON。"
    )
    events = extract_json(selection_result)
    if isinstance(events, dict):
        events = [events]
    print(f"   选出 {len(events)} 条事件")

    # 去重：如果与昨天的新闻明显重复，换一批
    try:
        today_dt = datetime.strptime(today, "%Y-%m-%d") if "-" in today else datetime.strptime(today, "%Y%m%d")
        from datetime import timedelta
        yday = (today_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        yday_file = OUTPUT_DIR / f"{yday}.json"
        if yday_file.exists():
            ydata = json.loads(yday_file.read_text(encoding="utf-8"))
            yesterdays_titles = [e.get("title", "") for e in ydata.get("events", [])]
            todays_titles = [e.get("title", "") for e in events]

            def extract_tokens(title: str) -> set:
                # 用双字组（bigram）精确匹配中文新闻标题
                clean = title.replace("：","").replace("，","").replace("、","").replace(" ","").replace("？","").replace("！","")
                return {clean[i:i+2] for i in range(len(clean)-1)}

            yday_tokens = set()
            for t in yesterdays_titles:
                yday_tokens |= extract_tokens(t)

            overlaps = 0
            for t in todays_titles:
                tokens = extract_tokens(t)
                common = len(tokens & yday_tokens)
                if common >= 2:  # 至少2个关键词重叠就算重复
                    overlaps += 1

            print(f"   与昨天关键词重叠: {overlaps}/3 条")
            if overlaps >= 2:
                print(f"   ⚠️ 重叠度过高，通知 LLM 换一批...")
                avoid_hint = "、".join([t[:30] for t in yesterdays_titles])
                retry_prompt = EVENT_SELECTION_PROMPT.format(news_summaries=news_text[:3000])
                retry_prompt += f"\n\n【特别注意】请务必避免以下昨天已分析的话题：\n{avoid_hint}\n请从其他新闻中选 3 条完全不同的事件。"
                retry_result = await call_llm(retry_prompt, "请按要求选出3条全新事件，必须避开已提示的话题。")
                retry_events = extract_json(retry_result)
                if isinstance(retry_events, dict):
                    retry_events = [retry_events]
                if retry_events and len(retry_events) >= 2:
                    events = retry_events
                    print(f"   ✅ 已更换为全新事件")
    except Exception as e:
        print(f"   ⚠️ 去重跳过（{e}）")

    # 4. 逐条生成分析
    all_results = []
    for i, event in enumerate(events):
        print(f"\n📝 正在生成第{i+1}条事件分析：{event.get('title', 'N/A')[:40]}...")

        analysis_result = await call_llm(
            ANALYSIS_PROMPT.format(event=json.dumps(event, ensure_ascii=False)),
            "请按要求生成深度分析并输出JSON。"
        )
        analysis = extract_json(analysis_result)

        # 合并事件元信息和分析结果
        # LLM 可能返回中文或英文键名，统一处理
        raw_title = (
            event.get("title") or event.get("标题") or
            event.get("event_title") or event.get("name") or ""
        )
        raw_summary = (
            event.get("summary") or event.get("摘要") or
            event.get("description") or event.get("brief") or ""
        )
        raw_impact = (
            event.get("impact") or event.get("影响评级") or
            event.get("rating") or event.get("stars") or 4
        )
        raw_tags = (
            event.get("tags") or event.get("标签") or
            event.get("keywords") or event.get("categories") or []
        )

        full_event = {
            "id": f"event-{i+1:03d}",
            "title": raw_title,
            "summary": raw_summary,
            "source": "36氪 · 八点一氪",
            "date": display_date,
            "impact": raw_impact,
            "tags": raw_tags,
            **analysis
        }
        all_results.append(full_event)

    # 5. 挑选今日名言：从所有事件的多维视角中选一句最契合今日主题的
    print("\n💬 正在从多维视角中挑选今日名言...")
    candidate_quotes = []
    for ev in all_results:
        for p in ev.get("perspectives", []):
            q = p.get("quote", "")
            src = p.get("source", "")
            if q and src and len(q) < 60:
                candidate_quotes.append({"text": q, "source": src})

    if candidate_quotes:
        pick_prompt = f"""以下是从今日新闻分析的多维视角中摘录的{len(candidate_quotes)}条名言：
{json.dumps(candidate_quotes, ensure_ascii=False, indent=2)}

请从中挑选 1 条最有道理、最契合今日事件主题的名言作为"今日名言"，
以 JSON 输出：{{"text": "选中的名言原文", "source": "对应的出处"}}
必须从候选中挑选，不得自创。仅输出 JSON。"""
        pick_result = await call_llm(pick_prompt, "请从候选名言中挑选1条输出JSON。")
        daily_quote = extract_json(pick_result)
        if not daily_quote or "text" not in daily_quote:
            daily_quote = candidate_quotes[0]
    else:
        daily_quote = {"text": "天下难事，必作于易", "source": "老子 · 道德经"}
    print(f"   今日名言：「{daily_quote['text']}」——{daily_quote['source']}")

    # 6. 存储结果
    today_date = today
    output_file = OUTPUT_DIR / f"{today_date}.json"

    output_data = {
        "generated_at": datetime.now().isoformat(),
        "date": today_date,
        "daily_quote": daily_quote,
        "events": all_results
    }

    output_file.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n💾 分析结果已保存到：{output_file}")

    # 同时写入 latest.json（供首页读取）
    latest_file = OUTPUT_DIR / "latest.json"
    latest_file.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   已同步写入：{latest_file}")

    # 追加往期索引 history.json
    history_file = OUTPUT_DIR / "history.json"
    history = []
    if history_file.exists():
        try:
            history = json.loads(history_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            history = []
    history = [h for h in history if h.get("date") != today_date]
    history.insert(0, {
        "date": today_date,
        "events": [{"id": e["id"], "title": e["title"], "summary": e["summary"][:80]} for e in all_results]
    })
    history = history[:30]
    history_file.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   往期索引已更新（共 {len(history)} 天）")

    # 5. 推送通知
    if all_results:
        hero = all_results[0]
        print(f"\n📤 正在推送通知...")
        await push_notification(
            event_title=hero["title"],
            event_summary=hero["summary"],
            event_id=hero["id"],
            base_url=base_url
        )

    print("\n" + "=" * 60)
    print("  ✅ 每日更新完成")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
