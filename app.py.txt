from flask import Flask, request, jsonify
import openai
import datetime
import os

# 从环境变量读取 API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

MODEL_PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60}  # 美元/M token，官方定价
}

# 存储待办事项
tasks = []

# 存储会话历史：示例结构 { "default": [{"role": "user", "content": "..."}, ...] }
conversation_history = {}

def calculate_cost(model, input_tokens, output_tokens):
    """根据输入和输出 token 数计算费用"""
    if model not in MODEL_PRICING:
        return 0
    price = MODEL_PRICING[model]
    input_cost = (input_tokens / 1_000_000) * price["input"]
    output_cost = (output_tokens / 1_000_000) * price["output"]
    return input_cost + output_cost

def ask_secretary(session_id, user_prompt):
    """调用 GPT-4o-mini 并保留对话历史"""
    # 获取该 session 的历史对话
    if session_id not in conversation_history:
        conversation_history[session_id] = [
            {"role": "system", "content": "你是我的私人AI秘书，帮我记录待办、提醒、查询信息，并在对话中保持记忆。"}
        ]

    # 添加新用户消息到历史
    conversation_history[session_id].append({"role": "user", "content": user_prompt})

    # 调用 API
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=conversation_history[session_id]
    )

    answer = response.choices[0].message["content"]

    # 将助手回复加入历史
    conversation_history[session_id].append({"role": "assistant", "content": answer})

    usage = response.usage
    total_cost = calculate_cost("gpt-4o-mini", usage.prompt_tokens, usage.completion_tokens)

    return answer, usage.prompt_tokens, usage.completion_tokens, total_cost

@app.route("/")
def index():
    return "✅ AI秘书已在线运行（支持多轮记忆）"

@app.route("/add_task", methods=["POST"])
def add_task():
    task = request.json.get("task")
    tasks.append({"task": task, "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")})
    return jsonify({"status": "success", "tasks": tasks})

@app.route("/chat", methods=["POST"])
def chat():
    session_id = request.json.get("session_id", "default")  # 用来区分不同用户会话
    prompt = request.json.get("prompt", "")

    answer, in_tokens, out_tokens, cost = ask_secretary(session_id, prompt)

    return jsonify({
        "answer": answer,
        "input_tokens": in_tokens,
        "output_tokens": out_tokens,
        "cost_usd": round(cost, 6),
        "session_id": session_id
    })

@app.route("/reset_session", methods=["POST"])
def reset_session():
    session_id = request.json.get("session_id", "default")
    if session_id in conversation_history:
        del conversation_history[session_id]
    return jsonify({"status": "success", "message": f"会话 {session_id} 已重置"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
