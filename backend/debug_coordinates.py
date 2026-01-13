"""
调试脚本：对比分析 API 调用差异
用于排查 AI Studio 和后端调用坐标不一致的问题
"""
import os
import sys
import json
import base64
from google import genai
from google.genai import types
from PIL import Image
from PIL import ImageOps
import io

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL = "gemini-3-flash-preview"

# 与后端完全一致的提示词
SYSTEM_INSTRUCTION = """Role: 你是一位精通计算机视觉和图像解析的专家，擅长对图像中的关键点进行像素级分析和坐标归一化计算，同时精通人类遗传学特征分析。
Task: 请分析上传的图片，精准定位图中孩子鼻尖的位置，计算脸部宽度比例，并对比父母与孩子的面部特征识别遗传相似性。

**Coordinate System Definition (严格遵守):**
*   原点 (0,0)：位于图片的左上角。
*   终点 (100,100)：位于图片的右下角。
*   X 轴：从左向右延伸，范围 0 到 100。
*   Y 轴：从上向下延伸，范围 0 到 100。

**Key Points to Identify:**
*   **face_center (鼻尖坐标)**: 请仔细观察孩子鼻子的轮廓，找到鼻尖（最突出点）的正中心位置。
*   **face_width (脸部宽度比例)**: 测量孩子面部左右最宽处（通常为两颊边缘）的距离，并将其转换为占整张图片宽度的百分比（0-100 之间的数值）。

**核心分析任务（遗传特征）：**
**分析部位（固定7项，严禁增减）：**
1. 眉毛、2. 眼睛、3. 鼻子、4. 嘴巴、5. 脸型、6. 头型、7. 总结

**关于分数：**
*   子项分数：根据相似程度客观打分（50-99）。
*   **总结分数**：综合判定孩子与父母的整体相似度百分比（取整数），无需严格等于平均值。

**输出格式：**
直接返回纯 JSON。

**JSON 结构：**
{
  "face_center": { "x": 整数(0-100), "y": 整数(0-100) },
  "face_width": 整数(0-100),
  "analysis_results": [
    {
    "part": "固定名称(眉毛/眼睛/鼻子/嘴巴/脸型/头型/总结)",
      "similar_to": "Father" 或 "Mother",
      "similarity_score": 整数(50-99),
      "description": "内容要求见下文'关于文案'"
    }
  ]
}

**关于文案（description）：**
1.  **普通部位（眉毛/眼睛等）**：30-50字。幽默点评具体特征细节。
2.  **总结（Summary）**：**80-120字**。请包含以下层次：
    *   **特征融合**：点评父母特征在孩子脸上的奇妙化学反应（如"爸爸的英气+妈妈的柔美"）。
    *   **气质神态**：从面相趣味推测宝宝性格（如"机灵鬼"、"淡定哥"、"治愈系"）。
    *   **未来寄语**：一句温暖或幽默的成长祝福。
"""

def prepare_image_like_backend(
    file_bytes: bytes,
    content_type: str = "image/jpeg",
    *,
    max_dim: int = 8192,
    max_bytes: int = 20 * 1024 * 1024,
) -> tuple[bytes, str, dict]:
    """
    模拟后端 prepare_image_for_gemini 的逻辑：
    - 尽量保持原始字节（对齐 AI Studio）
    - 必要时做 EXIF 方向矫正/压缩/转 JPEG

    返回：处理后的图片 bytes、mime_type、以及尺寸信息
    """
    img = Image.open(io.BytesIO(file_bytes))
    original_size = img.size

    exif = getattr(img, "getexif", lambda: None)()
    orientation = int(exif.get(274, 1) or 1) if exif else 1

    within_dim = max(img.size) <= max_dim
    within_bytes = len(file_bytes) <= max_bytes

    if content_type == "image/jpeg" and within_dim and within_bytes and orientation == 1:
        return file_bytes, content_type, {
            "original": original_size,
            "processed": original_size,
            "ratio": 1.0,
            "reencoded": False,
            "orientation": orientation,
        }
    
    # 统一方向
    img = ImageOps.exif_transpose(img)
    
    # 转换为 RGB
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    
    # 按比例缩放
    if max(img.size) > max_dim:
        ratio = max_dim / max(img.size)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    
    processed_size = img.size
    
    # 转为 JPEG bytes
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=95)
    
    return buffer.getvalue(), "image/jpeg", {
        "original": original_size,
        "processed": processed_size,
        "ratio": processed_size[0] / original_size[0] if original_size[0] > 0 else 1,
        "reencoded": True,
        "orientation": orientation,
    }


def call_gemini_simple(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    use_thinking: bool = False,
    label: str = "测试",
):
    """
    简化的 Gemini 调用，只获取鼻尖坐标
    """
    client = genai.Client(api_key=API_KEY)
    
    # 简化的 Schema，只关注坐标
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "face_center": {
                "type": "OBJECT",
                "properties": {
                    "x": {"type": "INTEGER"},
                    "y": {"type": "INTEGER"}
                },
                "required": ["x", "y"]
            },
            "face_width": {"type": "INTEGER"}
        },
        "required": ["face_center", "face_width"]
    }
    
    # 简化提示词，只要坐标
    simple_prompt = """请分析这张孩子的照片，找出鼻尖的精确位置。

坐标系定义：
- 原点 (0,0) 在图片左上角
- 终点 (100,100) 在图片右下角
- X 轴从左到右 0→100
- Y 轴从上到下 0→100

请输出鼻尖坐标 face_center 和脸部宽度百分比 face_width。"""
    
    parts = [
        types.Part.from_text(text=simple_prompt),
        types.Part.from_text(text="孩子照片："),
        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
    ]
    
    contents = [types.Content(role="user", parts=parts)]
    
    config_kwargs = {
        "max_output_tokens": 1024,
        "response_mime_type": "application/json",
        "response_schema": response_schema,
    }
    
    if use_thinking:
        config_kwargs["thinking_config"] = types.ThinkingConfig(include_thoughts=True)
    
    print(f"\n{'='*60}")
    print(f"🧪 {label}")
    print(f"   Thinking: {'开启' if use_thinking else '关闭'}")
    print(f"{'='*60}")
    
    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(**config_kwargs)
    )
    
    result_text = response.text
    # 提取 JSON
    start_idx = result_text.find('{')
    end_idx = result_text.rfind('}')
    if start_idx != -1 and end_idx != -1:
        result = json.loads(result_text[start_idx:end_idx+1])
    else:
        result = json.loads(result_text)
    
    print(f"   结果: face_center = ({result['face_center']['x']}, {result['face_center']['y']})")
    print(f"         face_width = {result.get('face_width', 'N/A')}")
    
    return result


def main(image_path: str):
    print("\n" + "🔬 Gemini API 坐标精度对比测试 ".center(60, "="))
    
    # 读取原始图片
    with open(image_path, "rb") as f:
        original_bytes = f.read()

    # 粗略推断原图 mime_type（用于避免“字节是 PNG 但声明成 JPEG”）
    try:
        img_probe = Image.open(io.BytesIO(original_bytes))
        fmt = (img_probe.format or "").upper()
        original_mime = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}.get(fmt, "image/jpeg")
    except Exception:
        original_mime = "image/jpeg"
    
    # 处理图片（模拟后端）
    processed_bytes, processed_mime, size_info = prepare_image_like_backend(original_bytes)
    
    print(f"\n📷 图片信息:")
    print(f"   原始尺寸: {size_info['original']}")
    print(f"   处理后尺寸: {size_info['processed']}")
    print(f"   缩放比例: {size_info['ratio']:.4f}")
    print(f"   是否重编码: {'是' if size_info.get('reencoded') else '否'}")
    print(f"   EXIF 方向: {size_info.get('orientation')}")
    
    # 测试 1: 原图 + 无 Thinking
    result1 = call_gemini_simple(original_bytes, mime_type=original_mime, use_thinking=False, label="原图 + 无 Thinking")
    
    # 测试 2: 原图 + 有 Thinking
    result2 = call_gemini_simple(original_bytes, mime_type=original_mime, use_thinking=True, label="原图 + 有 Thinking")
    
    # 测试 3: 压缩图 + 无 Thinking
    result3 = call_gemini_simple(processed_bytes, mime_type=processed_mime, use_thinking=False, label="后端实际发送图 + 无 Thinking")
    
    # 测试 4: 压缩图 + 有 Thinking
    result4 = call_gemini_simple(processed_bytes, mime_type=processed_mime, use_thinking=True, label="后端实际发送图 + 有 Thinking")
    
    # 汇总对比
    print("\n" + " 结果汇总 ".center(60, "="))
    print(f"{'配置':<30} | {'X':>5} | {'Y':>5} | {'Width':>6}")
    print("-" * 60)
    print(f"{'原图 + 无 Thinking':<30} | {result1['face_center']['x']:>5} | {result1['face_center']['y']:>5} | {result1.get('face_width', 'N/A'):>6}")
    print(f"{'原图 + 有 Thinking':<30} | {result2['face_center']['x']:>5} | {result2['face_center']['y']:>5} | {result2.get('face_width', 'N/A'):>6}")
    print(f"{'压缩图 + 无 Thinking':<30} | {result3['face_center']['x']:>5} | {result3['face_center']['y']:>5} | {result3.get('face_width', 'N/A'):>6}")
    print(f"{'压缩图 + 有 Thinking':<30} | {result4['face_center']['x']:>5} | {result4['face_center']['y']:>5} | {result4.get('face_width', 'N/A'):>6}")
    print("=" * 60)
    
    # 分析差异
    print("\n📊 差异分析:")
    x_diff = abs(result1['face_center']['x'] - result3['face_center']['x'])
    y_diff = abs(result1['face_center']['y'] - result3['face_center']['y'])
    print(f"   原图 vs 压缩图 差异: X={x_diff}, Y={y_diff}")
    
    if x_diff > 5 or y_diff > 5:
        print("   ⚠️ 图片压缩导致了显著的坐标偏差！")
        print("   💡 建议：不压缩图片，或提高压缩质量")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python debug_coordinates.py <图片路径>")
        print("示例: python debug_coordinates.py test_child.jpg")
        sys.exit(1)
    
    main(sys.argv[1])
