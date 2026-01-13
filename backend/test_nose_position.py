#!/usr/bin/env python3
"""
测试 Gemini API (REST 版本) - 避免 SDK 卡顿问题
"""
import os
import sys
import json
import base64
import requests
from dotenv import load_dotenv

# 加载 .env
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-3-flash-preview" # 使用更广泛支持的模型名称进行测试

if not API_KEY:
    print("错误: 未找到 GEMINI_API_KEY")
    sys.exit(1)

if len(sys.argv) < 2:
    print("用法: python test_nose_position.py <图片路径>")
    sys.exit(1)

image_path = sys.argv[1]
if not os.path.exists(image_path):
    print(f"错误: 图片不存在 {image_path}")
    sys.exit(1)

# 读取并编码图片
with open(image_path, "rb") as f:
    image_data = base64.b64encode(f.read()).decode("utf-8")

url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"

headers = {
    "Content-Type": "application/json"
}

payload = {
    "contents": [{
        "parts": [
            {"text": "Find the coordinates of the child's nose tip. Range 0-100. Return JSON: {\"nose_x\": int, \"nose_y\": int}"},
            {
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": image_data
                }
            }
        ]
    }],
    "generationConfig": {
        "response_mime_type": "application/json",
        "response_schema": {
            "type": "OBJECT",
            "properties": {
                "nose_x": {"type": "INTEGER"},
                "nose_y": {"type": "INTEGER"}
            }
        }
    }
}

print(f"正在通过 REST API 调用 {MODEL}...")
try:
    # 打印完整请求信息 (为了便于调试和对比，截断 base64 图片数据)
    log_payload = payload.copy()
    # 深度复制以免修改原 payload (虽然这里只是读取)
    import copy
    log_payload = copy.deepcopy(payload)
    # 截断 base64 显示
    for content in log_payload.get('contents', []):
        for part in content.get('parts', []):
            if 'inline_data' in part:
                part['inline_data']['data'] = "<BASE64_IMAGE_DATA_TRUNCATED>"
    
    print("\n--- Request Details ---")
    print(f"URL: {url}")
    print("Headers:", json.dumps(headers, indent=2))
    print("Payload:", json.dumps(log_payload, indent=2))
    print("-----------------------\n")

    # 设置 15 秒超时，防止无限卡死
    response = requests.post(url, headers=headers, json=payload, timeout=15)
    
    if response.status_code == 200:
        result = response.json()
        print("Raw Response:", json.dumps(result, indent=2))
        try:
            content = result['candidates'][0]['content']['parts'][0]['text']
            coords = json.loads(content)
            print(f"\n✅ 成功获取坐标: X={coords.get('nose_x')}, Y={coords.get('nose_y')}")
        except Exception as e:
            print(f"解析内容失败: {e}")
    else:
        print(f"API 错误: {response.status_code} - {response.text}")

except requests.exceptions.Timeout:
    print("❌ 请求超时！请检查网络连接或代理设置。")
except requests.exceptions.ConnectionError:
    print("❌ 连接失败！无法连接到 Google API。")
except Exception as e:
    print(f"❌ 发生异常: {e}")
