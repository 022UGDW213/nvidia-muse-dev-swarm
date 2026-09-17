#!/usr/bin/env python3
"""Minimal NVIDIA free-tier client (OpenAI-compatible).

Get a key at https://build.nvidia.com (free tier) and export it:
    export NVIDIA_API_KEY="nvapi-..."

Never hardcode or commit your key.
"""
import json
import os
import sys
import urllib.request

ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL = os.environ.get("NVIDIA_MODEL", "moonshotai/kimi-k3")


def chat(prompt, image_url=None, stream=True):
    key = os.environ.get("NVIDIA_API_KEY")
    if not key:
        sys.exit("Set NVIDIA_API_KEY first: export NVIDIA_API_KEY='nvapi-...'")
    content = [{"type": "text", "text": prompt}]
    if image_url:
        content.append({"type": "image_url",
                        "image_url": {"url": image_url}})
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": content}],
        "temperature": 1,
        "max_tokens": 4096,
        "stream": stream,
    }
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream" if stream else "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        print("HTTP", resp.status)
        if not stream:
            print(json.dumps(json.load(resp), indent=2)[:2000])
            return
        for raw in resp:
            line = raw.decode().strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                delta = json.loads(data)["choices"][0]["delta"]
                print(delta.get("reasoning_content", "") +
                      delta.get("content", ""), end="", flush=True)
            except (KeyError, IndexError, json.JSONDecodeError):
                pass
    print()


if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Say hi in one sentence."
    image = sys.argv[2] if len(sys.argv) > 2 else None
    chat(prompt, image_url=image)
