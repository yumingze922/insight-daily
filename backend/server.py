"""
每日深度思辨 —— FastAPI 后端服务
提供思辨对话、新闻分析等API接口
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# 添加当前目录到 path
sys.path.insert(0, str(Path(__file__).parent))

from llm_client import LLMClient
from prompts import SPECULATIVE_GUIDE_PROMPT


# === 配置加载 ===
def load_config():
    config_path = Path(__file__).parent.parent / "config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


config = load_config()

# === FastAPI 应用 ===
app = FastAPI(
    title="每日深度思辨 API",
    description="AI产品经理思维训练工具后端服务",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === LLM 客户端 ===
llm = LLMClient(config.get("llm", {}))


# === 数据模型 ===
class DialogueStartRequest(BaseModel):
    news_id: str
    news_title: str
    news_summary: str

class DialogueRespondRequest(BaseModel):
    news_id: str
    news_title: str
    news_summary: str
    phase: int
    user_message: str
    history: list = []

class NoteGenerateRequest(BaseModel):
    news_id: str
    news_title: str
    news_summary: str
    dialogue_history: list = []


# === 对话阶段上下文 ===
PHASE_CONTEXT = {
    1: {
        "name": "设问",
        "instruction": "这是对话的开始。请提出一个开放性的核心问题，引导用户表达对事件的初步看法。问题应该触及事件的根本逻辑，而不是表面现象。不要给答案，只提问。问题不超过3句话。"
    },
    2: {
        "name": "追问",
        "instruction": "基于用户刚才的回答，进行深度追问。挑战其假设前提，或者指出推理中的跳跃。引入一个新的学科视角（如经济学、政治学、心理学、管理学等任选其一）提出追问。问题不超过3句话。"
    },
    3: {
        "name": "多学科碰撞",
        "instruction": "从两个以上学科视角来审视这个事件。可以是中华古籍的古典智慧搭配一个现代理论（如博弈论、前景理论、颠覆式创新等），让用户看到同一个事件在不同透镜下的样貌。引用必须准确（典籍注明出处，现代理论点明学者或理论名）。然后提出一个整合性的问题。总长度不超过200字。"
    },
    4: {
        "name": "独见注入",
        "instruction": "给出一个与主流观点不同的原创见解。以\u201c我有一个不太一样的看法\u201d开头。这个见解应该有独特的分析框架，有逻辑支撑。然后邀请用户评判这个见解。总长度不超过200字。"
    },
    5: {
        "name": "总结升华",
        "instruction": "感谢用户的深入参与。用一句古典智慧做最后的点睛之笔。预告即将生成的思辨笔记。语气温暖而有力。总长度不超过100字。"
    }
}


# === 对话状态存储（内存） ===
dialogue_sessions: dict = {}


# === API 路由 ===

@app.get("/api/health")
async def health_check():
    """健康检查"""
    api_available = bool(llm.api_key)
    return {
        "status": "ok",
        "api_available": api_available,
        "model": llm.model,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/dialogue/start")
async def start_dialogue(req: DialogueStartRequest):
    """开始思辨对话 - 返回第一阶段问题"""
    try:
        news_context = f"新闻标题：{req.news_title}\n新闻摘要：{req.news_summary}"

        phase_info = PHASE_CONTEXT[1]
        prompt = SPECULATIVE_GUIDE_PROMPT.format(
            news_context=news_context,
            current_phase=phase_info["name"],
            dialogue_history="（对话刚刚开始）"
        ) + f"\n\n具体要求：{phase_info['instruction']}"

        if llm.api_key:
            response = await llm.chat([], system_prompt=prompt)
        else:
            response = _get_mock_response(req.news_id, 1)

        # 存储会话
        dialogue_sessions[req.news_id] = {
            "history": [],
            "current_phase": 1,
            "news_context": news_context
        }

        return {
            "phase": 1,
            "phase_name": phase_info["name"],
            "message": response,
            "total_phases": 5
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dialogue/respond")
async def respond_dialogue(req: DialogueRespondRequest):
    """对话交互 - 用户回答后返回追问"""
    try:
        session = dialogue_sessions.get(req.news_id, {})
        history = session.get("history", [])

        # 记录用户消息
        history.append({"role": "user", "content": req.user_message})

        # 下一阶段
        next_phase = req.phase + 1
        if next_phase > 5:
            return {
                "phase": 5,
                "phase_name": "总结升华",
                "message": "我们的对话已经完成了全部五个阶段。现在让我为你生成今日的思辨笔记。",
                "dialogue_complete": True
            }

        phase_info = PHASE_CONTEXT[next_phase]

        # 构建对话历史
        history_text = "\n".join([
            f"{'用户' if h['role'] == 'user' else '系统'}：{h['content']}"
            for h in history[-6:]  # 最近6条
        ])

        prompt = SPECULATIVE_GUIDE_PROMPT.format(
            news_context=session.get("news_context", ""),
            current_phase=phase_info["name"],
            dialogue_history=history_text
        ) + f"\n\n具体要求：{phase_info['instruction']}"

        if llm.api_key:
            response = await llm.chat([], system_prompt=prompt)
        else:
            response = _get_mock_response(req.news_id, next_phase)

        # 记录系统消息
        history.append({"role": "assistant", "content": response})

        # 更新会话
        dialogue_sessions[req.news_id] = {
            "history": history,
            "current_phase": next_phase,
            "news_context": session.get("news_context", "")
        }

        return {
            "phase": next_phase,
            "phase_name": phase_info["name"],
            "message": response,
            "dialogue_complete": next_phase >= 5
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dialogue/note")
async def generate_note(req: NoteGenerateRequest):
    """生成思辨笔记"""
    try:
        history_text = "\n".join([
            f"{'用户' if h['role'] == 'user' else '系统'}：{h['content']}"
            for h in req.dialogue_history
        ])

        if llm.api_key:
            from prompts import NOTE_GENERATION_PROMPT
            prompt = NOTE_GENERATION_PROMPT.format(
                dialogue_content=history_text,
                news_context=f"{req.news_title}\n{req.news_summary}"
            )
            response = await llm.chat([], system_prompt=prompt)
            try:
                note = json.loads(response)
            except json.JSONDecodeError:
                note = {"raw": response}
        else:
            note = _get_mock_note(req.news_id)

        return {"note": note}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dialogue/stream")
async def stream_dialogue(
    news_id: str,
    phase: int,
    user_message: str = ""
):
    """流式对话（SSE）"""
    try:
        session = dialogue_sessions.get(news_id, {})
        history = session.get("history", [])

        if user_message:
            history.append({"role": "user", "content": user_message})

        next_phase = phase + 1 if phase < 5 else phase
        phase_info = PHASE_CONTEXT.get(next_phase, PHASE_CONTEXT[1])

        history_text = "\n".join([
            f"{'用户' if h['role'] == 'user' else '系统'}：{h['content']}"
            for h in history[-6:]
        ])

        prompt = SPECULATIVE_GUIDE_PROMPT.format(
            news_context=session.get("news_context", ""),
            current_phase=phase_info["name"],
            dialogue_history=history_text
        ) + f"\n\n具体要求：{phase_info['instruction']}"

        async def generate():
            if llm.api_key:
                async for chunk in llm.chat_stream([], system_prompt=prompt):
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
            else:
                text = _get_mock_response(news_id, next_phase)
                # 模拟流式输出
                for i, char in enumerate(text):
                    yield f"data: {json.dumps({'content': char})}\n\n"
                    import asyncio
                    if i % 5 == 0:
                        await asyncio.sleep(0.02)

            yield "data: [DONE]\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Mock 响应（无API Key时使用） ===
def _get_mock_response(news_id: str, phase: int) -> str:
    """返回模拟的对话响应"""
    mock_responses = {
        "event-001": {
            1: "在你看来，台积电宣布在美国追加1000亿美元投资建设第三座晶圆厂，这背后最根本的驱动力是什么？是商业逻辑还是政治压力？说说你的直觉判断。",
            2: "有意思。但从博弈论的角度来看——台积电把最先进的产能放在美国，是否意味着它放弃了过去\"台湾制造、全球销售\"的均衡策略？当博弈的参与者（美国、中国、客户）都在博弈中改变策略时，台积电的新均衡点在哪里？",
            3: "让我们用两个透镜看这件事。\n\n第一个透镜，《孙子兵法·形篇》说：\n「先为不可胜，以待敌之可胜」\n——先确保自己立于不败之地，再等待战胜对手的机会。\n\n第二个透镜，迈克尔·波特的\"五力模型\"：供应商的议价能力取决于其不可替代性。\n\n台积电在做的，是不是同时用\"不可胜\"的策略保护自己，又在重塑行业\"五力\"格局中的位置？你怎么看这两个透镜的交汇？",
            4: "我有一个不太一样的看法：主流分析都把台积电赴美建厂解读为\"被迫的政治妥协\"，但我认为台积电正在利用地缘政治焦虑，从一家\"代工厂\"进化为\"地缘政治的定价者\"。过去它的护城河是技术（纳米制程），未来它的护城河将是\"不可替代的地缘政治价值\"——当美国和中国的半导体战略都离不开你时，你就拥有了超越技术的定价权。你认同这个判断吗？",
            5: "很好，我们的对话已经从产业分工延伸到地缘战略的层面。正如《孙子兵法》所言：\"上兵伐谋\"——最高明的竞争是在战略层面决胜负。今天我们从经济学、管理学、古典兵法等不同透镜审视了同一个事件——这种\"多棱镜思维\"就是思辨训练的核心价值。让我帮你整理今天的思辨笔记。"
        }
    }

    default_responses = {
        1: "在你看来，这件事背后最根本的驱动力是什么？不要想得太复杂——说说你的直觉判断。",
        2: "你提到一个很好的角度。但如果换个学科视角——比如从经济学的博弈论角度来看，这件事会呈现出怎样不同的面貌？",
        3: "让我们从两个不同的学科透镜来看这件事。\n\n古典智慧：《周易》说「穷则变，变则通，通则久」——变化本身就是不变的规律。\n\n现代理论：克莱顿·克里斯坦森的"颠覆式创新"理论告诉我们，最大的威胁往往来自视野之外。\n\n这两个视角在这一点上交汇了。你怎么看？",
        4: "我有一个不太一样的看法。跳出常规的分析框架，这件事或许揭示了一个更深层的趋势——而这个趋势目前还没有被主流观点充分讨论。你怎么看这个判断？",
        5: "谢谢你的深入参与。今天的对话让我们从多个学科的透镜中审视了同一个事件。让我帮你把思考整理成笔记。"
    }

    responses = mock_responses.get(news_id, default_responses)
    return responses.get(phase, default_responses.get(phase, "..."))


def _get_mock_note(news_id: str) -> dict:
    """返回模拟的思辨笔记"""
    return {
        "coreProposition": "基于我们的对话，核心命题已经逐渐清晰。每一个重大事件背后，都交织着商业逻辑、政治博弈和人性认知的多重力量。",
        "mainstreamView": "主流观点往往只看到了事件的一面——要么是商业逻辑，要么是政治博弈。但真相往往更复杂。",
        "alternativeView": "我们跳出常规框架后看到的图景是：当事方可能在利用看似被动的处境，重新定义自己在博弈中的位置。",
        "multidisciplinaryInsight": "从经济学的博弈论、管理学的五力模型、古典兵法的战略智慧等多个学科视角来看，同一个事件在不同透镜下展现出截然不同的层次。这正是思辨训练的核心价值——拥有多棱镜般的思维。",
        "personalJudgment": "综合各方视角，我认为这件事的真正意义在于它展示了当代世界的根本特征：商业与政治的边界正在消失，技术能力与地缘价值的边界也在模糊。在这样一个世界里，谁能同时理解多个维度的逻辑，谁就拥有真正的洞察力。",
        "actionTakeaway": "当遇到重大事件时，尝试用至少三个学科的透镜来审视它。经济学告诉你利益如何分配，心理学告诉你人们为什么这样决策，古典智慧告诉你人性的不变规律。这种练习做多了，洞察力自然就长出来了。"
    }


# === 启动 ===
if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  每日深度思辨 API 服务")
    print("  访问 http://localhost:8765/docs 查看API文档")
    print("=" * 60)
    if not llm.api_key:
        print("  提示: 未检测到API Key，将使用Mock模式")
        print("  在 config.json 中配置 api_key 启用真实LLM")
    uvicorn.run(app, host="0.0.0.0", port=8765)
