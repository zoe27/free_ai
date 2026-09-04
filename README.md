# free-ai-gateway

自建的免费 AI API 聚合网关，暴露 OpenAI 兼容的 `/v1/chat/completions` 接口，后端按优先级自动 fallback 多个免费模型来源（Gemini、Groq、OpenRouter `:free` 模型、本地 Ollama 等）。

需求详情见 [docs/requirements.md](docs/requirements.md)，架构设计见 [docs/architecture.md](docs/architecture.md)，各来源 key 申请方式见 [docs/getting-keys.md](docs/getting-keys.md)。

## 快速开始

```bash
# 1. 创建虚拟环境并安装
python3 -m venv .venv
.venv/bin/pip install -e .

# 2. 配置 API Key
cp env.example .env
# 编辑 .env，填入至少一个免费来源的 key（比如 GROQ_API_KEY，注册即送、秒批）
# 没配 key 的 provider 会被自动跳过，不用全填

# 3. 启动
.venv/bin/uvicorn free_ai_gateway.main:app --host 0.0.0.0 --port 8000
# 或者：.venv/bin/python -m free_ai_gateway.main
```

## 调用方式

跟调用 OpenAI 接口完全一样，把 `base_url` 换成本网关地址即可：

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "default", "messages": [{"role": "user", "content": "你好"}]}'
```

- `model` 填 `providers.yaml` 里定义的**别名**（如 `default` / `smart`），网关会按该别名的优先级链自动尝试、失败自动 fallback 到下一个来源
- 也可以用 `provider/真实模型名` 的写法直连某一个来源跳过 fallback，例如 `"model": "groq/llama-3.3-70b-versatile"`
- 想看当前有哪些别名可用：`curl http://localhost:8000/v1/models`
- 如果在 `.env` 里设了 `GATEWAY_TOKEN`，调用时要带 `Authorization: Bearer <token>`（网关暴露给其他设备/内网穿透时建议设置，避免被白嫖；纯本地用可以不设）

## 新增一个免费来源

编辑 `providers.yaml`，加一个 provider 定义 + 在 `aliases` 里加一步即可，不用改代码（前提是该来源提供 OpenAI 兼容的 `/chat/completions` 端点，目前列的来源基本都支持）。

## 项目结构

```
src/free_ai_gateway/
├── main.py              # FastAPI 入口：/v1/chat/completions、/v1/models
├── config.py            # 加载 .env + providers.yaml
├── schemas.py            # OpenAI 兼容请求模型 + ProviderError
├── router.py              # 别名解析 + provider fallback 循环
├── health.py              # provider 失败后的临时 cooldown（简单熔断）
└── providers/
    ├── base.py                # Provider 接口
    ├── openai_compatible.py   # 通用 adapter（覆盖大部分来源）
    └── registry.py            # 按配置实例化所有启用的 provider
providers.yaml            # provider 定义 + model 别名链
env.example              # 复制为 .env 后填 key
tests/
```

## 待实现（二期）

- [ ] 流式响应（`stream=true`，目前会直接 400）
- [ ] 单元测试
- [ ] 部署方式：本地常驻 + 内网穿透，还是云端免费托管
