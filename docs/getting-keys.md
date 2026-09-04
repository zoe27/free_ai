# 各来源 API Key 申请方式

> ⚠️ 免费额度、注册流程会经常变（Groq 之前的免费模型就整批下线过），这里记录的是大致路径，具体条款以各平台官网当时展示的为准。拿到 key 之后填到 `.env` 对应变量，`providers.yaml` 不用改。

## 🟢 优先申请（免费额度宽松 / 注册简单）

### Gemini — `GEMINI_API_KEY`
- 入口：https://aistudio.google.com → 左侧 "Get API key"
- 账号：Google 账号直接登录，不需要绑卡
- 免费额度：Gemini Flash 系列个人开发者免费层比较宽松，有按分钟/按天的请求数限制
- 备注：这是 Google AI Studio 的 key，不是 Google Cloud Vertex AI 的（后者要开计费账号，不要走错）

### Groq — `GROQ_API_KEY`
- 入口：https://console.groq.com → API Keys 页面 → Create API Key
- 账号：邮箱或 Google/GitHub 登录
- 免费额度：免费调用开源模型（Llama/Qwen/GPT-OSS 系列等），限流按 RPM/TPM 算，具体看控制台 Limits 页面
- 备注：免费模型列表变动频繁（之前 Llama-3.3 那批就下线了），报 404/model_not_found 时去控制台 "Models" 页面查当前可用的模型 ID，改 `providers.yaml` 里对应那行

### DeepSeek — `DEEPSEEK_API_KEY`
- 入口：https://platform.deepseek.com → API keys → 创建 API key
- 账号：手机号或微信登录
- 免费额度：新用户通常有一小笔赠送额度，价格本身也很低；不是长期免费，用完要付费

### 智谱 GLM — `ZHIPU_API_KEY`
- 入口：https://open.bigmodel.cn → 右上角 API Keys
- 账号：手机号注册
- 免费额度：新用户注册送一笔免费 tokens，`glm-4-flash` 常年对个人开发者免费（以官网当时公告为准）

## 🟡 值得申请（额度有限，但多一个 fallback 没坏处）

### Moonshot Kimi — `MOONSHOT_API_KEY`
- 入口：https://platform.moonshot.cn → API Key 管理
- 账号：手机号注册
- 免费额度：新用户赠送额度，用完按量付费

### Qwen (通义千问 / DashScope) — `QWEN_API_KEY`
- 入口：https://dashscope.console.aliyun.com → 右上角 API-KEY 管理（需要阿里云账号，会引导你完成实名认证）
- 账号：阿里云账号（手机号即可注册，实名认证是阿里云平台强制要求，不是这个网关额外要求的）
- 免费额度：新用户有免费 tokens 额度，`qwen-turbo` 相对便宜/常有促销额度
- 备注：本项目用的是 DashScope 的 **OpenAI 兼容模式**（`compatible-mode/v1`），申请流程跟普通 DashScope key 一样，不用单独开兼容模式的权限

### 硅基流动 SiliconFlow — `SILICONFLOW_API_KEY`
- 入口：https://cloud.siliconflow.cn → API 密钥
- 账号：手机号/邮箱注册
- 免费额度：平台上标 "免费" 的开源模型（通常是 7B/8B 级别）可以零成本调用，注册本身也常送一点体验金
- 备注：免费模型的名字要去控制台的模型广场核对，别直接照抄 `providers.yaml` 里写的示例模型名

### Together AI — `TOGETHER_API_KEY`
- 入口：https://api.together.ai → Sign Up → Settings → API Keys
- 账号：邮箱或 Google/GitHub 登录
- 免费额度：注册常送一笔免费额度（额度用尽后不是长期免费），平台上也有少数带 "Free" 标的模型

### Mistral (La Plateforme) — `MISTRAL_API_KEY`
- 入口：https://console.mistral.ai → API Keys
- 账号：邮箱注册
- 免费额度：有免费/低价层（"Experiment" 计划），部分小模型限流下免费，具体额度看控制台

## ⚪ 可选 / 本地扩展

### Ollama（本地，不需要 key）
- 安装：https://ollama.com/download，按你的操作系统装好
- 用法：装完之后本地跑 `ollama pull qwen2.5:7b`（或你想要的其他模型），Ollama 会自动在 `http://localhost:11434` 起一个服务
- `.env` 里 `OLLAMA_BASE_URL` 默认就是这个地址，不用改；网关的 `providers.yaml` 已经把 ollama 配好了，不需要填任何 API key
- 好处：真正的 0 成本兜底，前面所有来源都失败/限流时还能用本地模型顶上

### OpenRouter — `OPENROUTER_API_KEY`
- 入口：https://openrouter.ai → Sign In → Keys
- 账号：邮箱/Google/GitHub 登录
- 免费额度：带 `:free` 后缀的模型（比如 `meta-llama/llama-3.3-70b-instruct:free`）免费调用，但限流很严（按天/按分钟请求数都很低），建议放在 fallback 链靠后位置，别当主力
- 备注：`providers.yaml` 已经配好了这个来源，只是排在链的比较后面

### Cerebras — `CEREBRAS_API_KEY`
- 入口：https://cloud.cerebras.ai → API Keys
- 账号：邮箱注册
- 免费额度：官方说个人开发者能免费跑开源模型，速度是几家里最快的
- ⚠️ 实测坑：申请到 key 后调用直接 402 `Payment required`（`gpt-oss-120b`、`gemma-4-31b` 都试过，一样报错），说明这个账号的免费额度没有自动生效，得去控制台 Billing 页面看一下要不要先绑定/激活才能拿到免费额度。没弄好之前网关会自动跳过这个来源，不影响其他来源正常用

## 填完 key 之后

1. 确认 `.env` 里变量名跟上面对应（比如 `MISTRAL_API_KEY=xxx`），不需要重启电脑，重启网关服务就生效
2. 让我帮你跑一次真实调用测试：告诉我填了哪个,我会用 `.venv/bin/python` 检查 config 是否加载到,再发一个真实请求验证 model 名对不对
3. 如果某个来源报 404/model_not_found，大概率是 `providers.yaml` 里写的 model 名过期了，去对应控制台的模型列表核对后改一下即可，不用改代码
