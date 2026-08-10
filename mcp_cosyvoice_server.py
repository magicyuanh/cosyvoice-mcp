#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CosyVoice3 TTS MCP server (stdio) —— 最小实现，仅依赖 Python 标准库。
对接本地 CosyVoice TTS 服务 (默认 http://127.0.0.1:10096)。

MCP 客户端配置示例 (claude_desktop_config.json / WorkBuddy mcp.json 等)：
  "command": "python",
  "args":    [ "/path/to/mcp_cosyvoice_server.py" ]

环境变量（可选）：
  COSYVOICE_TTS_URL  服务地址，默认 http://127.0.0.1:10096
  COSYVOICE_OUT      输出 WAV 目录，默认 <脚本所在目录>/output
"""
import sys
import os
import json
import datetime
import urllib.parse
import urllib.request
import urllib.error
import wave
import mimetypes

TTS_BASE = os.environ.get("COSYVOICE_TTS_URL", "http://127.0.0.1:10096")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.environ.get("COSYVOICE_OUT", os.path.join(SCRIPT_DIR, "output"))
os.makedirs(OUT_DIR, exist_ok=True)


def send(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def err(msg):
    return {"content": [{"type": "text", "text": f"错误: {msg}"}], "isError": True}


def post_form(url, fields):
    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return urllib.request.urlopen(req, timeout=600)


def post_multipart(url, fields, files):
    """multipart/form-data 上传，files: {name: (filename, filepath)}"""
    boundary = "----wb" + os.urandom(8).hex()
    parts = []
    for k, v in fields.items():
        parts.append(
            (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n"
             f"{v}\r\n").encode("utf-8")
        )
    for k, (fname, fpath) in files.items():
        with open(fpath, "rb") as f:
            content = f.read()
        ct = mimetypes.guess_type(fname)[0] or "application/octet-stream"
        parts.append(
            (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"; "
             f"filename=\"{fname}\"\r\nContent-Type: {ct}\r\n\r\n").encode("utf-8")
            + content + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(parts)
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    return urllib.request.urlopen(req, timeout=600)


def save_wav(pcm, sr):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(OUT_DIR, f"tts_{ts}.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm)
    return path


TOOLS = [
    {
        "name": "text_to_speech",
        "description": (
            "使用 CosyVoice3 将文本合成为语音，返回生成的 WAV 文件路径。"
            "支持指定音色ID（如 default / longyingcheng 等），留空使用默认音色。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "要合成的文本（中文效果最佳）"},
                "voice_id": {"type": "string",
                             "description": "音色ID，如 default / longyingcheng 等；留空用默认音色"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "zero_shot_clone",
        "description": (
            "使用 CosyVoice3 零样本音色克隆：提供一段参考音频(WAV 16kHz 单声道, 5-15秒) "
            "及其对应的转录文本，即可用该音色合成新语音。返回生成的 WAV 文件路径。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "要合成的文本（中文效果最佳）"},
                "prompt_text": {"type": "string",
                                "description": "参考音频中实际说出的内容，必须一字不差，"
                                               "建议以 'You are a helpful assistant.<|endofprompt|>' 开头"},
                "prompt_wav": {"type": "string",
                               "description": "参考音频文件的绝对路径 (WAV, 16kHz, 单声道)"},
            },
            "required": ["text", "prompt_text", "prompt_wav"],
        },
    },
    {
        "name": "tts_health",
        "description": "查询本地 CosyVoice TTS 服务健康状态（模型、采样率、可用音色列表）。",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def handle_call(name, args):
    if name == "text_to_speech":
        text = (args or {}).get("text")
        if not text or not text.strip():
            return err("text 不能为空")
        voice_id = (args or {}).get("voice_id")
        fields = {"text": text}
        if voice_id:
            fields["voice_id"] = voice_id
        try:
            resp = post_form(TTS_BASE + "/tts/stream", fields)
            pcm = resp.read()
            sr = int(resp.headers.get("X-Sample-Rate", "24000"))
        except urllib.error.HTTPError as e:
            return err(f"TTS 服务返回错误: {e.code} {e.read().decode('utf-8', 'ignore')[:200]}")
        except Exception as e:
            return err(f"调用 TTS 失败: {e}")
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(OUT_DIR, f"tts_{ts}.wav")
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes(pcm)
        return {
            "content": [{
                "type": "text",
                "text": (f"✅ 语音已生成\n路径: {path}\n"
                         f"采样率: {sr}Hz\n大小: {len(pcm)//2} 样本 / {len(pcm)} 字节"),
            }],
            "isError": False,
        }

    elif name == "zero_shot_clone":
        text = (args or {}).get("text")
        prompt_text = (args or {}).get("prompt_text")
        prompt_wav = (args or {}).get("prompt_wav")
        if not text or not text.strip():
            return err("text 不能为空")
        if not prompt_text or not prompt_text.strip():
            return err("prompt_text 不能为空")
        if not prompt_wav or not os.path.isfile(prompt_wav):
            return err(f"参考音频不存在: {prompt_wav}")
        try:
            resp = post_multipart(
                TTS_BASE + "/tts/zero_shot",
                {"text": text, "prompt_text": prompt_text},
                {"prompt_wav": (os.path.basename(prompt_wav), prompt_wav)},
            )
            pcm = resp.read()
            sr = int(resp.headers.get("X-Sample-Rate", "24000"))
        except urllib.error.HTTPError as e:
            return err(f"TTS 服务返回错误: {e.code} {e.read().decode('utf-8', 'ignore')[:200]}")
        except Exception as e:
            return err(f"调用 TTS 失败: {e}")
        path = save_wav(pcm, sr)
        return {
            "content": [{
                "type": "text",
                "text": (f"✅ 音色克隆语音已生成\n路径: {path}\n"
                         f"采样率: {sr}Hz\n大小: {len(pcm)//2} 样本 / {len(pcm)} 字节"),
            }],
            "isError": False,
        }

    elif name == "tts_health":
        try:
            d = json.loads(urllib.request.urlopen(TTS_BASE + "/health", timeout=10).read())
            return {
                "content": [{"type": "text",
                             "text": json.dumps(d, ensure_ascii=False, indent=2)}],
                "isError": False,
            }
        except Exception as e:
            return err(f"查询健康状态失败: {e}")

    return err(f"未知工具: {name}")


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue
        method = req.get("method")
        rid = req.get("id")
        params = req.get("params", {}) or {}
        if method == "initialize":
            send({
                "jsonrpc": "2.0", "id": rid,
                "result": {
                    "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "cosyvoice-tts", "version": "1.0.0"},
                },
            })
        elif method == "notifications/initialized":
            pass
        elif method == "ping":
            send({"jsonrpc": "2.0", "id": rid, "result": {}})
        elif method == "tools/list":
            send({"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}})
        elif method == "tools/call":
            name = params.get("name")
            args = params.get("arguments", {})
            send({"jsonrpc": "2.0", "id": rid, "result": handle_call(name, args)})
        else:
            if rid is not None:
                send({"jsonrpc": "2.0", "id": rid,
                      "error": {"code": -32601, "message": f"method not found: {method}"}})


if __name__ == "__main__":
    main()
