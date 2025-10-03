# AI秘书（云端部署版）

可直接部署到 Render 的 AI 秘书，可以记录事务、提醒、查询信息。

## 部署到 Render
1. Fork 或上传这个仓库到 GitHub。
2. 登录 https://render.com
3. 点击 New Web Service，选择本仓库。
4. 设置环境变量：
   OPENAI_API_KEY = 你的 OpenAI API Key
5. 部署成功后就可以用 https://你的域名/chat 调用秘书。