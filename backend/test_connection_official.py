import asyncio
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
import logging

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-3-flash-preview"  # 强制使用指定模型进行测试

print(f"------------ 模型可用性诊断 ------------")
print(f"API Key: {API_KEY[:6]}******" if API_KEY else "API Key: 未找到")
print(f"Target Model: {MODEL}")
print(f"SDK Version: {genai.__version__}")
print(f"----------------------------------------")

async def test_specific_model():
    if not API_KEY:
        print("❌ 错误: 未设置 GEMINI_API_KEY")
        return

    try:
        print(f"正在初始化 Google GenAI 客户端...")
        client = genai.Client(api_key=API_KEY)
        
        print(f"正在发送请求到 {MODEL}...")
        
        # 尝试最简单的纯文本请求
        response = client.models.generate_content(
            model=MODEL,
            contents="Hello, verifying model availability.",
            config=types.GenerateContentConfig(
                temperature=0.1
            )
        )
        
        print(f"✅ 模型 {MODEL} 调用成功!")
        print(f"响应内容: {response.text}")
        
    except Exception as e:
        print(f"❌ 模型 {MODEL} 调用失败")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误详情: {e}")
        
        # 如果是 404 或 400，通常意味着模型名称不对或未对该 Key 开放
        if "404" in str(e):
             print("\n⚠️  诊断提示: 404 错误通常表示模型名称不正确，或者该模型尚未对您的 API Key 开放权限。")
        elif "400" in str(e):
             print("\n⚠️  诊断提示: 400 错误可能是参数格式问题。")

if __name__ == "__main__":
    asyncio.run(test_specific_model())
