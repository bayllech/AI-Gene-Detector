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
SYSTEM_INSTRUCTION = """Role: 你是一位精通计算机视觉和图像解析的专家，擅长对图像中的关键点进行像素级分析和坐标归一化计算，同时精通人脸特征比对。
Task: 请分析上传的图片，精准定位图中孩子鼻尖的位置，计算脸部宽度比例，并对比父母与孩子的五官特征识别相似度。

**Coordinate System Definition (严格遵守):**
*   原点 (0,0)：位于图片的左上角。
*   终点 (100,100)：位于图片的右下角。
*   X 轴：从左向右延伸，范围 0 到 100。
*   Y 轴：从上向下延伸，范围 0 到 100。

**Key Points to Identify:**
*   **face_center (鼻尖坐标)**: 请仔细观察孩子鼻子的轮廓，找到鼻尖（最突出点）的正中心位置。
*   **face_width (脸部宽度比例)**: 测量孩子面部左右最宽处（通常为两颊边缘）的距离，并将其转换为占整张图片宽度的百分比（0-100 之间的数值）。

**核心分析任务（面部特征）：**
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

**关于文案（description）- 极其重要：**
1.  **禁词表**: 严禁出现“基因”、“遗传”、“DNA”、“生物学”、“血缘”等词汇。请使用“特征”、“神态”、“五官”、“相貌”、“复刻”等词替代。
2.  **风格**：轻松、娱乐、幽默、温暖。
3.  **普通部位（眉毛/眼睛等）**：30-50字。幽默点评具体特征细节。
4.  **总结（Summary）**：**80-120字**。请包含以下层次：
    *   **特征融合**：点评父母特征在孩子脸上的奇妙结合（如“完美复刻了爸爸的英气和妈妈的柔美”）。
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
        child_mime_type: str = "image/jpeg",
        father_image: Optional[bytes] = None,
        father_mime_type: Optional[str] = None,
        mother_image: Optional[bytes] = None,
        mother_mime_type: Optional[str] = None,
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
            parts.append(
                types.Part.from_bytes(
                    data=father_image, mime_type=father_mime_type or "image/jpeg"
                )
            )
        else:
            parts.append(types.Part.from_text(text="父亲照片：未提供"))

        if mother_image:
            parts.append(types.Part.from_text(text="母亲照片："))
            parts.append(
                types.Part.from_bytes(
                    data=mother_image, mime_type=mother_mime_type or "image/jpeg"
                )
            )
        else:
            parts.append(types.Part.from_text(text="母亲照片：未提供"))
        
        # 动态提示词：处理单亲情况 (逻辑优化 v2)
        # 核心策略：单亲模式下，所有相似度必须相对于"存在的家长"。
        # 像对方 = 不像我 (分数 100 - X)
        
        single_parent_mode = False
        target_role = ""

        if father_image and not mother_image:
            single_parent_mode = True
            target_role = "Father"
            parts.append(types.Part.from_text(text="""
            **重要约束 (Single Parent Mode):**
            1. 用户仅上传了【父亲】照片。
            2. JSON 中所有 analysis_results 的 `similar_to` 字段必须严格强制为 "Father"。**严禁出现 "Mother"。**
            3. 评分逻辑：
               - 如果部位像父亲：`similarity_score` 给高分 (60-99)。
               - 如果部位**不像**父亲 (或像缺席的母亲)：`similarity_score` 必须给**低分 (10-40)**，代表相似度低。
            4. description 文案：请只点评"孩子与父亲在xx处的相似或不同"，**不要提及母亲**。
            """))
            
        elif mother_image and not father_image:
            single_parent_mode = True
            target_role = "Mother"
            parts.append(types.Part.from_text(text="""
            **重要约束 (Single Parent Mode):**
            1. 用户仅上传了【母亲】照片。
            2. JSON 中所有 analysis_results 的 `similar_to` 字段必须严格强制为 "Mother"。**严禁出现 "Father"。**
            3. 评分逻辑：
               - 如果部位像母亲：`similarity_score` 给高分 (60-99)。
               - 如果部位**不像**母亲 (或像缺席的父亲)：`similarity_score` 必须给**低分 (10-40)**，代表相似度低。
            4. description 文案：请只点评"孩子与母亲在xx处的相似或不同"，**不要提及父亲**。
            """))

        parts.append(types.Part.from_text(text="孩子照片（请基于此图输出坐标）："))
        parts.append(types.Part.from_bytes(data=child_image, mime_type=child_mime_type))
        
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
                        mime_type = getattr(p.inline_data, "mime_type", None) or "unknown"
                        log_parts.append({"inline_data": f"<{mime_type} BASE64_IMAGE_DATA_TRUNCATED>"})
                log_contents.append({"role": c.role, "parts": log_parts})
            
            logger.info(f"\n🚀 [GEMINI REQUEST START] ----------------------------------\n"
                        f"Target Model: {self.model_name}\n"
                        f"Payload Summary: {json.dumps(log_contents, indent=2, ensure_ascii=False)}\n"
                        f"-------------------------------------------------------------")

            # 调用 Gemini API
            # 注意：不再使用 response_schema，改回纯文本模式以避免 SDK 在空响应时崩溃
            # 我们通过 response_mime_type="application/json" 提示模型输出 JSON
            
            # 增加重试机制，应对 503 Overloaded
            max_retries = 3
            retry_delay = 2 # seconds
            import time
            from google.genai.errors import ServerError
            
            response = None
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    logger.info(f"正在调用 Gemini API (尝试 {attempt + 1}/{max_retries})...")
                    start_time = time.time()
                    
                    response = self.client.models.generate_content(
                        model=self.model_name,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_INSTRUCTION,
                            temperature=settings.gemini_temperature,
                            max_output_tokens=8192,
                            response_mime_type="application/json",
                            safety_settings=[
                                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
                                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                            ]
                        )
                    )
                    
                    duration = time.time() - start_time
                    logger.info(f"Gemini API 调用成功，耗时: {duration:.2f}s")
                    
                    # 显式检查 response 是否为空
                    if not response:
                        logger.error("Gemini 返回了空对象 (None)")
                        raise ValueError("Gemini API returned None")
                    
                    # 尝试获取文本
                    try:
                        result_text = response.text
                    except Exception as e:
                        logger.error(f"无法从 Gemini 响应中获取文本: {e}")
                        # 打印一下 dir(response) 看看有什么
                        logger.info(f"Response attributes: {dir(response)}")
                        raise ValueError(f"Failed to extract text from response: {e}")

                    if not result_text:
                        logger.error(f"Gemini 返回了空文本 (response.text is empty). Finish reason: {response.candidates[0].finish_reason if response.candidates else 'Unknown'}")
                        raise ValueError("Gemini response text is empty")
                    
                    # 记录原始返回（截取前500字符以防日志爆炸，但足以排查 JSON 格式问题）
                    logger.info(f"Gemini 原始返回 (前500字符): {result_text[:500]}...")

                    # 清理 Markdown 代码块标记 ```json ... ```
                    cleaned_text = result_text.strip()
                    if cleaned_text.startswith("```"):
                        # 去掉第一行 (```json) 和最后一行 (```)
                        lines = cleaned_text.split('\n')
                        if len(lines) >= 2:
                            # 找到第一个 ``` 和最后一个 ```
                            first_code_block = -1
                            last_code_block = -1
                            for i, line in enumerate(lines):
                                if line.strip().startswith("```"):
                                    if first_code_block == -1:
                                        first_code_block = i
                                    else:
                                        last_code_block = i
                            
                            if first_code_block != -1 and last_code_block != -1:
                                cleaned_text = "\n".join(lines[first_code_block+1 : last_code_block])
                            else:
                                # 简单的fallback
                                cleaned_text = cleaned_text.replace("```json", "").replace("```", "")
                    
                    logger.info("开始解析 JSON...")
                    # 如果成功调用，跳出重试循环
                    break
                except ServerError as e:
                    if e.code == 503:
                        last_error = e
                        logger.warning(f"Gemini 服务过载 (503)，正在重试 ({attempt + 1}/{max_retries})...")
                        time.sleep(retry_delay * (attempt + 1)) # 线性退避
                    else:
                        raise e # 其他 API 错误直接抛出
                except Exception as e:
                    raise e # 其他异常直接抛出
            
            # 如果重试完还是失败
            if response is None and last_error:
                raise last_error
            
            # 解析响应
            # result_text = response.text # This line is now handled inside the retry loop
            
            # 兼容性检查：如果 text 依然为空，抛出更明确的错误而不是崩在 SDK 内部
            if not result_text:
                error_msg = "Gemini 返回了空内容 (None)。可能被安全策略拦截，或模型拒绝回答。"
                # 尝试检查是否有候选对象的安全评级信息
                try:
                    if response.candidates:
                         error_msg += f" 候选结果: {response.candidates[0].finish_reason}"
                except:
                    pass
                logger.error(error_msg)
                raise ValueError(error_msg)

            # logger.info(f"Gemini 原始响应: {result_text[:200]}...")
            
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
                # 数据清洗与兜底 (Single Parent Enforcer)
                # -------------------------------------------------------
                if single_parent_mode and target_role:
                    if "analysis_results" in result:
                        for item in result["analysis_results"]:
                            current_role = item.get("similar_to")
                            current_score = item.get("similarity_score", 50)
                            
                            # 如果 AI 返回了不存在的家长 (叛逆情况)
                            if current_role != target_role:
                                logger.warning(f"单亲模式纠正: {item['part']} 指向了 {current_role}, 强制重定向至 {target_role}")
                                item["similar_to"] = target_role
                                # 既然 AI 认为像缺席方，说明不像当前方 -> 反转分数
                                # 例: 像 Mother 80% -> 像 Father 20%
                                item["similarity_score"] = 100 - current_score
                                
                                # 简单的文案修饰 (可选，防止文案里还提缺席方)
                                # item["description"] = f"(自动校正) {item['description']}"
                
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
