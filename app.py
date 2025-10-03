from flask import Flask, request, jsonify, render_template_string
import openai
import datetime
import os

# 从环境变量读取 API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

# 模型价格（美元 / M token）
MODEL_PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60}
}

# 存储待办事项
tasks = []

# 存储会话历史 {"session_id": [{"role": "user", "content": "..."}, ...]}
conversation_history = {}

def calculate_cost(model, input_tokens, output_tokens):
    """计算 token 用量的价格（美元）"""
    if model not in MODEL_PRICING:
        return 0
    price = MODEL_PRICING[model]
    input_cost = (input_tokens / 1_000_000) * price["input"]
    output_cost = (output_tokens / 1_000_000) * price["output"]
    return input_cost + output_cost

def ask_secretary(session_id, user_prompt):
    """调用 GPT-4o-mini 并保留对话历史"""
    if session_id not in conversation_history:
        conversation_history[session_id] = [
            {"role": "system", "content": "你是我的私人AI秘书，帮我记录待办、提醒、查询信息，并在对话中保持记忆。"}
        ]

    conversation_history[session_id].append({"role": "user", "content": user_prompt})

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=conversation_history[session_id]
    )

    answer = response.choices[0].message["content"]

    # 保存助手回复到历史
    conversation_history[session_id].append({"role": "assistant", "content": answer})

    usage = response.usage
    total_cost = calculate_cost("gpt-4o-mini", usage.prompt_tokens, usage.completion_tokens)

    return answer, usage.prompt_tokens, usage.completion_tokens, total_cost

# ======== HTML 聊天界面模板 ========
chat_html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>AI秘书聊天</title>
</head>
<body>
    <h2>✅ AI秘书已在线运行（支持多轮记忆）</h2>
    <form method="post">
        <input name="prompt" placeholder="请输入你的问题" style="width:300px">
        <button type="submit">发送</button>
    </form>
    {% if answer %}
        <p><b>你：</b>{{ prompt }}</p>
        <p><b>AI：</b>{{ answer }}</p>
        <p>Token消耗：输入 {{ in_tokens }} / 输出 {{ out_tokens }} / 费用约 ${{ cost_usd }}</p>
    {% endif %}
</body>
</html>
"""

# 首页网页聊天
@app.route("/", methods=["GET", "POST"])
def index():
    prompt = ""
    answer = ""
    in_tokens = 0
    out_tokens = 0
    cost = 0

    if request.method == "POST":
        prompt = request.form.get("prompt", "")
        answer, in_tokens, out_tokens, cost = ask_secretary("web_default", prompt)

    return render_template_string(chat_html,
                                  prompt=prompt,
                                  answer=answer,
                                  in_tokens=in_tokens,
                                  out_tokens=out_tokens,
                                  cost_usd=round(cost, 6))

# 添加待办事项
@app.route("/add_task", methods=["POST"])
def add_task():
    task = request.json.get("task")
    tasks.append({"task": task, "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")})
    return jsonify({"status": "success", "tasks": tasks})

# 聊天 API（供其他程序调用）
@app.route("/chat", methods=["POST"])
def chat():
    session_id = request.json.get("session_id", "default")  # 用户标识
    prompt = request.json.get("prompt", "")

    answer, in_tokens, out_tokens, cost = ask_secretary(session_id, prompt)

    return jsonify({
        "answer": answer,
        "input_tokens": in_tokens,
        "output_tokens": out_tokens,
        "cost_usd": round(cost, 6),
        "session_id": session_id
    })

# 重置会话
@app.route("/reset_session", methods=["POST"])
def reset_session():
    session_id = request.json.get("session_id", "default")
    if session_id in conversation_history:
        del conversation_history[session_id]
    return jsonify({"status": "success", "message": f"会话 {session_id} 已重置"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
