"""
Gemini AI 服务
负责调用 Google Gemini API 进行面部特征分析
"""
from google import genai
from google.genai import types
from app.core.config import get_settings
import json
import base64
import ast
import re
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

# Gemini 系统提示词（来自设计文档）
SYSTEM_INSTRUCTION = """你是一位精通计算机视觉与人类遗传学的专家。你的任务是分析家庭照片，通过对比父母与孩子的面部特征，识别遗传相似性。

**核心任务：**
1. **分析遗传特征**：对比孩子与父母的特定五官部位，判断更像谁。
2. **定位脸部中心**：在孩子照片中，找出**鼻尖**的精确位置作为脸部中心参考点。

**分析部位（固定7项，严禁增减）：**
1. 眉毛、2. 眼睛、3. 鼻子、4. 嘴巴、5. 脸型、6. 头型、7. 总结

**关于分数：**
*   子项分数：根据相似程度客观打分（50-99）。
*   **总结分数**：综合判定孩子与父母的整体相似度百分比（取整数），无需严格等于平均值。

**坐标系定义（极其重要）：**
*   图片**左上角**是 (0, 0)。
*   图片**右下角**是 (100, 100)。
*   **x 轴**：从左到右，0→100。
*   **y 轴**：从上到下，0→100。
*   **示例**：如果鼻尖在图片正中央，则 face_center = {x: 50, y: 50}。
*   **示例**：如果鼻尖在图片右上角附近，则 face_center = {x: 80, y: 20}。
*   **示例**：如果鼻尖在图片左下角附近，则 face_center = {x: 20, y: 80}。

**关于 face_center：**
*   这是孩子**鼻尖**在图片中的精确位置。
*   请仔细观察孩子的鼻子，找到鼻尖的像素位置，然后转换为百分比坐标。

**关于 face_width：**
*   孩子脸部宽度（从左脸颊到右脸颊）占整个图片宽度的百分比（通常在 20-60 之间）。

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
    *   **特征融合**：点评父母特征在孩子脸上的奇妙化学反应（如“爸爸的英气+妈妈的柔美”）。
    *   **气质神态**：从面相趣味推测宝宝性格（如“机灵鬼”、“淡定哥”、“治愈系”）。
    *   **未来寄语**：一句温暖或幽默的成长祝福。
"""



class GeminiService:
    """Gemini AI 服务类"""
    
    def __init__(self):
        """初始化 Gemini 客户端"""
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model_name = settings.gemini_model
        logger.info(f"Gemini 服务已初始化，使用模型: {self.model_name}")
    
    async def analyze_family_photos(
        self,
        child_image: bytes,
        father_image: Optional[bytes] = None,
        mother_image: Optional[bytes] = None
    ) -> dict:
        """
        分析家庭照片，识别遗传特征
        """
        # 定义响应结构 (JSON Schema)
        response_schema = {
            "type": "OBJECT",
            "properties": {
                "face_center": {
                    "type": "OBJECT",
                    "description": "Nose tip position in percentage (0-100)",
                    "properties": {
                        "x": {"type": "INTEGER"},
                        "y": {"type": "INTEGER"}
                    },
                    "required": ["x", "y"]
                },
                "face_width": {
                    "type": "INTEGER",
                    "description": "Face width as percentage of image width (0-100)"
                },
                "analysis_results": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "part": {"type": "STRING"},
                            "similar_to": {"type": "STRING"},
                            "similarity_score": {"type": "INTEGER"},
                            "description": {"type": "STRING"}
                        },
                        "required": ["part", "similar_to", "similarity_score", "description"]
                    }
                }
            },
            "required": ["analysis_results", "face_center", "face_width"]
        }

        # 构建消息内容
        contents = []
        
        # 添加文本提示 (简化提示词，因为 Schema 已经掌管了结构)
        prompt_text = "分析家庭照片，识别面部特征遗传来源。严格按照定义的 JSON 格式输出。"
        
        # 添加图片（按顺序：父亲、母亲、孩子）
        parts = [types.Part.from_text(text=prompt_text)]
        
        if father_image:
            parts.append(types.Part.from_text(text="父亲照片："))
            parts.append(types.Part.from_bytes(data=father_image, mime_type="image/jpeg"))
        
        if mother_image:
            parts.append(types.Part.from_text(text="母亲照片："))
            parts.append(types.Part.from_bytes(data=mother_image, mime_type="image/jpeg"))
        
        parts.append(types.Part.from_text(text="孩子照片（请基于此图输出坐标）："))
        parts.append(types.Part.from_bytes(data=child_image, mime_type="image/jpeg"))
        
        contents.append(types.Content(role="user", parts=parts))
        try:
            # -------------------------------------------------------
            # 1. 打印请求日志 (Request Log)
            # -------------------------------------------------------
            log_contents = []
            for c in contents:
                # 深度复制以安全修改用于打印
                log_parts = []
                for p in c.parts:
                    if p.text:
                        log_parts.append({"text": p.text[:100] + "..." if len(p.text) > 100 else p.text})
                    elif p.inline_data:
                        log_parts.append({"inline_data": "<BASE64_IMAGE_DATA_TRUNCATED>"})
                log_contents.append({"role": c.role, "parts": log_parts})
            
            logger.info(f"\n🚀 [GEMINI REQUEST START] ----------------------------------\n"
                        f"Target Model: {self.model_name}\n"
                        f"Payload Summary: {json.dumps(log_contents, indent=2, ensure_ascii=False)}\n"
                        f"-------------------------------------------------------------")

            # 调用 Gemini API
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.5,
                    max_output_tokens=8192,
                    response_mime_type="application/json",
                    response_schema=response_schema
                )
            )
            
            # 解析响应
            result_text = response.text
            # logger.info(f"Gemini 原始响应: {result_text[:200]}...") # 移除旧的原始截断日志
            
            # 强化清洗逻辑
            try:
                # 寻找第一个 { 和最后一个 }
                start_idx = result_text.find('{')
                end_idx = result_text.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    cleaned_text = result_text[start_idx : end_idx + 1]
                else:
                    cleaned_text = result_text

                # 尝试标准解析
                result = json.loads(cleaned_text)
                
                # -------------------------------------------------------
                # 2. 打印响应日志 (Response Log)
                # -------------------------------------------------------
                logger.info(f"\n✅ [GEMINI RESPONSE END] ------------------------------------\n"
                            f"{json.dumps(result, indent=2, ensure_ascii=False)}\n"
                            f"-------------------------------------------------------------")

                return result

            except json.JSONDecodeError as e:
                logger.warning(f"标准 JSON 解析失败: {e}，尝试 AST 解析...")
                try:
                    # AST 容错
                    result = ast.literal_eval(cleaned_text)
                    if isinstance(result, dict):
                        return result
                    else:
                        raise ValueError("AST 解析结果不是字典")
                except Exception:
                    logger.error(f"解析彻底失败。\n原始文本: {result_text}")
                    raise ValueError(f"AI 返回数据异常: {str(e)}")
            
        except Exception as e:
            logger.error(f"Gemini API 调用异常: {str(e)}", exc_info=True)
            raise


# 创建服务单例
gemini_service = GeminiService()
