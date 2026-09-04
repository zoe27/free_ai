# 架构设计

## 1. 整体分层

```
Client (curl / SDK / IDE 插件)
        │  OpenAI 协议 (base_url 指向本网关)
        ▼
┌─────────────────────────────────────────┐
│ API 层  (FastAPI)                        │
│  POST /v1/chat/completions                │
│  GET  /v1/models                          │
└───────────────┬───────────────────────────┘
                │ OpenAI ChatCompletionRequest
                ▼
┌─────────────────────────────────────────┐
│ Router（路由/编排）                        │
│  - model 别名 → provider 候选链            │
│  - 按顺序尝试，失败/限流自动 fallback        │
│  - 记录每个 provider 的健康状态             │
└───────────────┬───────────────────────────┘
                │ 统一内部请求对象
                ▼
┌─────────────────────────────────────────┐
│ Provider Adapter 层（每来源一个模块）        │
│  Gemini / Groq / OpenRouter / Ollama /... │
│  职责：请求转译 + 调用 + 响应转译回 OpenAI 格式│
└───────────────┬───────────────────────────┘
                │ HTTP (httpx)
                ▼
        各免费模型来源的真实 API
```

核心原则：**API 层只认识 OpenAI 格式，Provider 层负责把差异吸收掉**，Router 是唯一知道"有哪些 provider、按什么顺序试"的地方。新增一个免费来源 = 写一个 Adapter + 注册到配置，不改其他任何层。

## 2. 模块划分（对应 `src/free_ai_gateway/`）

| 模块 | 职责 |
|---|---|
| `main.py` | FastAPI app，挂载路由，启动 uvicorn |
| `schemas.py` | OpenAI 兼容的请求/响应 Pydantic 模型（`ChatCompletionRequest/Response`，先支持非流式，流式作为二期） |
| `config.py` | 从 `.env` + `providers.yaml` 加载配置，产出 `ProviderConfig` 列表 |
| `router.py` | 核心路由逻辑：别名解析、fallback 循环、健康状态记录 |
| `health.py` | Provider 健康状态的内存态管理（配额耗尽/限流的临时降权） |
| `providers/base.py` | `Provider` 抽象基类：`async def chat_completion(request) -> ChatCompletionResponse` |
| `providers/gemini.py` `groq.py` `openrouter.py` `ollama.py` ... | 具体适配器，每个约 50–100 行 |
| `providers/registry.py` | 根据 `config.py` 的结果实例化所有启用的 Provider，供 router 使用 |

## 3. 关键设计决策（对应需求文档第 5 节的待确认项）

### 3.1 路由策略 — 建议：**按模型别名的固定优先级 fallback**，配额/限流触发临时降权

- 客户端请求里的 `model` 字段是一个**逻辑别名**，不是某个 provider 的真实模型名。例如：
  ```yaml
  # providers.yaml
  aliases:
    default:      # 日常聊天/写代码，优先快 / 免费额度宽松的
      - {provider: groq, model: llama-3.3-70b-versatile}
      - {provider: gemini, model: gemini-2.0-flash}
      - {provider: openrouter, model: "meta-llama/llama-3.3-70b-instruct:free"}
      - {provider: ollama, model: qwen2.5:7b}   # 兜底，本地跑
    smart:        # 需要更强推理时手动指定
      - {provider: gemini, model: gemini-2.0-pro}
      - {provider: openrouter, model: "deepseek/deepseek-r1:free"}
  ```
- Router 按顺序尝试候选，遇到 `429 / 5xx / timeout` 就换下一个，**同一次请求内对用户完全透明**。
- 也支持"直连"某个 provider：`model` 写成 `groq/llama-3.3-70b-versatile` 这种带命名空间的形式，跳过别名解析，方便调试单个来源。
- 为什么不做"自动按额度实时切换"：额度信息大多数免费 API 不暴露查询接口，做不到精确感知；用"失败即降级 + 一段时间后自动恢复"（见 3.2）比强行监控额度更现实、维护成本更低。

### 3.2 健康状态 / 简单熔断（`health.py`）

- 内存字典：`{provider_name: {"cooldown_until": ts, "fail_count": n}}`
- provider 返回 429/5xx → 记一次失败，短暂 cooldown（例如 60s，指数递增到上限，如 30min）
- cooldown 期间 router 跳过该 provider，直接试下一个候选
- 进程重启即重置——个人用场景不需要持久化这个状态，保持简单

### 3.3 Provider Adapter 接口

```python
class Provider(Protocol):
    name: str
    async def chat_completion(self, req: ChatCompletionRequest) -> ChatCompletionResponse: ...
```
- 每个 adapter 自己处理：认证方式差异（header/query key）、消息格式差异（如 Gemini 的 `contents` 结构）、错误码映射（统一转成网关内部的 `ProviderError(retryable: bool)`）
- Ollama adapter 特殊之处：不需要 API key，`base_url` 指向本地 `http://localhost:11434`，模型名直接透传

### 3.4 部署方式 — 先跑通本地单进程，架构不为此做妥协

- Phase 1（现在）：`uvicorn` 本地跑，只服务本机
- Phase 2（"其他设备也可用"）：两个候选都不影响上面的分层设计
  - 本地常驻 + 内网穿透（如 Tailscale / Cloudflare Tunnel）
  - 云端免费托管（如 Fly.io / Render 的免费额度）
- 建议：**加一个网关自身的简单 Bearer Token 校验**（一个固定 token，存在 `.env` 里），一旦网关被暴露到内网/公网之外，避免被白嫖。不算"多用户鉴权体系"，只是一个开关，成本几乎为零。

### 3.5 API Key 管理

- `.env`（本地文件，已在 `.gitignore`）存所有 provider 的 key，`config.py` 用 `python-dotenv` 加载
- 没配 key 的 provider 在 `registry.py` 里自动跳过（不报错、不进候选链）——这样"先接入哪几个"就是"先填哪几个 key"，不用改代码
- 限流监控：不做专门的监控系统；`health.py` 的 cooldown 记录 + 日志里打印"provider X 失败/降级"已经够个人用排查

## 4. 请求流程示例

```
POST /v1/chat/completions  {"model": "default", "messages": [...]}
  → Router: alias "default" → [groq, gemini, openrouter, ollama]
  → 尝试 groq → 429（限流）→ 记 cooldown → 试下一个
  → 尝试 gemini → 200 OK → 转成 OpenAI 格式返回给客户端
```
客户端全程无感知，只知道调了一个 OpenAI 兼容的接口。

## 5. 二期可选项（不在首批范围）

- 流式响应（SSE `stream=true`）
- `/v1/embeddings`（如果需要）
- 简单的用量统计面板（每 provider 调用次数/失败率，写到本地 sqlite）
