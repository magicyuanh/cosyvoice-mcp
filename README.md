# CosyVoice3 MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Server-black.svg)](https://modelcontextprotocol.io)
[![CosyVoice3](https://img.shields.io/badge/CosyVoice-3-red.svg)](https://github.com/FunAudioLLM/CosyVoice)

将 [Fun-CosyVoice3-0.5B-2512](https://github.com/fengin/Fun-CosyVoice3-0.5B-2512-Deploy) 本地 TTS 服务封装为 **MCP (Model Context Protocol) stdio server**。单文件、纯 Python 标准库实现，零第三方依赖，可接入 Claude Desktop / WorkBuddy 等任意支持 MCP 的客户端。

支持三个工具：

| 工具 | 功能 |
|---|---|
| `text_to_speech` | 文本 → 语音（可选 4 个预置音色） |
| `zero_shot_clone` | 零样本音色克隆：给一段参考音频 + 转录文本，用该音色说任意新文本 |
| `tts_health` | 查询 TTS 服务健康状态（模型、采样率、音色列表、GPU 显存） |

## 架构

```
┌─────────────────┐   stdio    ┌──────────────────────────┐   HTTP    ┌─────────────────────┐
│  MCP 客户端     │ ─────────▶ │  mcp_cosyvoice_server.py │ ────────▶ │  CosyVoice TTS 服务  │
│ (Claude/WorkBuddy)│ ◀───────── │  (本仓库, 纯标准库)      │ ◀────────  │  http://127.0.0.1:10096 │
└─────────────────┘   JSON-RPC  └──────────────────────────┘   PCM16   └─────────────────────┘
```

- 本仓库只含 **MCP 壳**：把 MCP JSON-RPC 调用翻译成对本地 TTS 服务的 HTTP 请求。
- TTS 服务本体（模型推理）由 [Fun-CosyVoice3-0.5B-2512-Deploy](https://github.com/fengin/Fun-CosyVoice3-0.5B-2512-Deploy) 提供，需单独部署，与本仓库解耦。
- 输出为 24kHz 单声道 PCM16，自动封装为 WAV 落盘到 `output/`（可用 `COSYVOICE_OUT` 覆盖）。

## 前置要求

1. **本地 TTS 服务已运行**：`http://127.0.0.1:10096`，实现 `/health`、`/tts/stream`、`/tts/zero_shot` 三个端点（参考上方的 Deploy 仓库）。
2. **Python 3.10+**（本脚本只用标准库，任意解释器均可）。

## 安装

```bash
git clone https://github.com/magicyuanh/cosyvoice-mcp.git
cd cosyvoice-mcp
# 无需 pip install —— 零依赖
```

## 配置（MCP 客户端）

### Claude Desktop

编辑 `claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "cosyvoice-tts": {
      "command": "python",
      "args": ["C:/path/to/cosyvoice-mcp/mcp_cosyvoice_server.py"]
    }
  }
}
```

### WorkBuddy

编辑 `~/.workbuddy/mcp.json`，追加：

```json
{
  "mcpServers": {
    "cosyvoice-tts": {
      "command": "python",
      "args": ["C:/path/to/cosyvoice-mcp/mcp_cosyvoice_server.py"]
    }
  }
}
```

保存后在 WorkBuddy 连接器管理 → 自定义连接器 → 找到 `cosyvoice-tts` → 点 **Trust** 启用。

### 环境变量（可选）

| 变量 | 默认值 | 说明 |
|---|---|---|
| `COSYVOICE_TTS_URL` | `http://127.0.0.1:10096` | TTS 服务地址 |
| `COSYVOICE_OUT` | `<脚本目录>/output` | WAV 输出目录 |

## 使用示例

### 常规合成

```
"用 CosyVoice 说：明天下午三点会议室 A 开评审会"
"用 longyingwan 女声读这段话：尊敬的各位来宾……"
```

### 零样本音色克隆

参考音频要求：**WAV、16kHz、单声道、5–15 秒、人声清晰无杂音**，并准备与音频**一字不差**的转录文本：

```
"用我录的声音克隆：参考音频 D:\myself.wav，里面说的是『我是xx，专注复杂系统交付二十年』。
 帮我把这段话用我的声音说出来：……"
```

### 健康检查

```
"TTS 服务正常吗？"
```

## 预置音色（`text_to_speech` 可选 `voice_id`）

| voice_id | 说明 |
|---|---|
| `default` | 默认音色 |
| `longyingcheng` | 男声 |
| `longyingwan` | 女声 |
| `longyingmu` | 女声 · 客服腔 |

## 合规提示

- 克隆他人声音需获得授权，请遵守当地法律法规与平台规则。
- TTS 服务端模型 Fun-CosyVoice3-0.5B-2512 为 Apache 2.0；部署仓库为 MIT。

## License

MIT
