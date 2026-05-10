# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import uvicorn
import logging
import time
import os
import base64
import json
import httpx
import requests
import re
from typing import Optional, List
from datetime import datetime, timedelta

from init_db import init_db
from routers.auth import router as auth_router
from routers.doctors import router as doctors_router

# ============== 日志配置 ==============
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============== 配置 ==============
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-7bb7e871e9014526aa7da9a8adafdc8e")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

# GNews API 配置
GNEWS_API_KEY = "3f14cf095ab0347b0184812cdf85ac6a"
GNEWS_BASE_URL = "https://gnews.io/api/v4"

# 图片生成配置
IMAGE_API_URL = os.environ.get("IMAGE_API_URL", "")
IMAGE_API_KEY = os.environ.get("IMAGE_API_KEY", "")

# ============== Lifespan（启动/关闭事件） ==============
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时自动初始化数据库（幂等）
    try:
        await init_db()
    except Exception as e:
        logger.warning(f"数据库初始化异常（可忽略非关键错误）: {e}")
    yield


# ============== FastAPI 初始化 ==============
app = FastAPI(title="AI助手接口", version="2.0", lifespan=lifespan)

# 注册路由
app.include_router(auth_router, prefix="/api/auth")
app.include_router(doctors_router, prefix="/api/doctors")

# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============== OpenAI 客户端 ==============
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    timeout=httpx.Timeout(120.0, connect=10.0),
    max_retries=0
)

# ============== 请求模型 ==============
class ChatRequest(BaseModel):
    user_input: str
    user_id: str
    agent_type: Optional[str] = "auto"
    file_type: Optional[str] = None
    file_data: Optional[str] = None
    file_name: Optional[str] = None

class ChatResponse(BaseModel):
    code: int
    answer: str
    agent: str
    image_url: Optional[str] = None
    news_data: Optional[List[dict]] = None
    processing_time: Optional[float] = None

# ============== Agent 配置 ==============
AGENT_CONFIGS = {
    "default": {
        "model": "deepseek-v4-flash",
        "system_prompt": "你是一个实用、简洁、友好的AI助手。回答要准确、有条理。",
        "thinking_mode": "non-thinking"
    },
    "emotion": {
        "model": "deepseek-v4-flash",
        "system_prompt": "你是一个温柔、善解人意的情绪陪伴师，善于倾听、安慰和鼓励。用温暖的话语回应用户的情绪。",
        "thinking_mode": "non-thinking"
    },
    "wiki": {
        "model": "deepseek-v4-pro",
        "system_prompt": "你是生活百科专家，回答准确、严谨、有条理，引用可靠知识来源。",
        "thinking_mode": "thinking"
    },
    "create": {
        "model": "deepseek-v4-pro",
        "system_prompt": "你是创意写作大师，擅长文案创作、诗歌、故事编写，语言优美富有想象力。",
        "thinking_mode": "thinking"
    },
    "news": {
        "model": "deepseek-v4-pro",
        "system_prompt": "你是一个实时新闻助手，只能基于搜索到的新闻内容回答用户问题。如果搜索结果中没有相关信息，请如实告知用户未找到相关新闻。回答要简洁明了，包含新闻标题、来源、时间和简要内容。",
        "thinking_mode": "thinking"
    },
    "image_analysis": {
        "model": "deepseek-v4-pro",
        "system_prompt": "你是专业的图像分析师，仔细描述图片内容，回答用户关于图片的问题。",
        "thinking_mode": "thinking_max"
    },
    "video_analysis": {
        "model": "deepseek-v4-pro",
        "system_prompt": "你是专业的视频分析师，分析视频内容并提供详细描述和建议。",
        "thinking_mode": "thinking_max"
    },
    "file_analysis": {
        "model": "deepseek-v4-pro",
        "system_prompt": "你擅长分析各类文档，提取关键信息，总结要点。",
        "thinking_mode": "thinking_max"
    },
    "image_generate": {
        "model": "image_gen",
        "system_prompt": "",
        "thinking_mode": ""
    }
}

# ============== 自动路由判断 ==============
def detect_agent(user_input: str, file_type: str = None) -> str:
    """
    自动判断应该使用哪个Agent
    优先级：文件 > 新闻意图 > 图片生成意图 > 情绪意图 > 知识意图 > 默认
    """
    
    # 1. 如果有文件上传，根据文件类型路由
    if file_type:
        if file_type == "image":
            return "image_analysis"
        elif file_type == "video":
            return "video_analysis"
        else:
            return "file_analysis"
    
    # 转换为小写，便于匹配
    user_input_lower = user_input.lower().strip()
    
    # 2. 检查是否是新闻检索意图
    news_keywords = [
        "新闻", "最新", "实时", "热点", "今天", "昨天", "报道",
        "发生了什么", "时事", "要闻", "近期", "最近", "新消息",
        "快讯", "动态", "更新", "新闻资讯", "科技新闻", "今日新闻",
        "头条", "热搜", "热点新闻", "最新消息"
    ]
    
    is_news_query = any(keyword in user_input_lower for keyword in news_keywords)
    
    if is_news_query:
        logger.info(f"检测到新闻查询: {user_input}")
        return "news"
    
    # 3. 检查是否是图片生成意图
    image_keywords = ["画图", "生成图片", "帮我画", "画一张", "生成一张图",
                      "image", "绘画", "创作图片", "画个", "画出", "作图"]
    if any(keyword in user_input_lower for keyword in image_keywords):
        return "image_generate"
    
    # 4. 检查是否是情绪类意图
    emotion_keywords = ["难过", "伤心", "焦虑", "开心", "兴奋", "失落", "压力",
                        "抑郁", "孤单", "emo", "心情", "烦", "累", "痛苦", "无奈"]
    if any(keyword in user_input_lower for keyword in emotion_keywords):
        return "emotion"
    
    # 5. 检查是否是知识类问题
    knowledge_patterns = ["是什么", "为什么", "怎么做", "如何", "区别",
                          "定义", "原理", "介绍", "什么意思", "怎么办"]
    if any(pattern in user_input_lower for pattern in knowledge_patterns):
        return "wiki"
    
    # 6. 默认使用日常助手
    return "default"

# ============== 新闻检索服务 ==============
class NewsService:
    def __init__(self):
        self.api_key = GNEWS_API_KEY
        self.base_url = GNEWS_BASE_URL
    
    async def search_news(self, query: str, days_back: int = 3, max_results: int = 5) -> dict:
        """
        搜索新闻
        返回: {"success": bool, "articles": list, "error": str}
        """
        # 提取关键词
        keywords = self._extract_keywords(query)
        
        # 如果没有有效关键词，使用默认
        if not keywords or len(keywords) < 2:
            keywords = "technology"
        
        try:
            # 构建请求参数
            params = {
                "q": keywords,
                "lang": "zh",
                "max": max_results,
                "apikey": self.api_key,
                "sortby": "publishedAt",
                "in": "title,description"
            }
            
            logger.info(f"新闻搜索参数: {params}")
            
            # 调用 GNews API
            response = requests.get(
                f"{self.base_url}/search",
                params=params,
                timeout=15
            )
            
            logger.info(f"GNews API 响应状态: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get("articles", [])
                
                if not articles:
                    logger.warning(f"未找到相关新闻，关键词: {keywords}")
                    return {
                        "success": True,
                        "articles": [],
                        "total": 0,
                        "query": keywords,
                        "message": "未找到相关新闻"
                    }
                
                # 格式化新闻数据
                formatted_articles = []
                for article in articles[:max_results]:
                    formatted_articles.append({
                        "title": article.get("title", ""),
                        "description": article.get("description", ""),
                        "content": article.get("content", ""),
                        "url": article.get("url", ""),
                        "image_url": article.get("image", ""),
                        "publishedAt": article.get("publishedAt", ""),
                        "source": article.get("source", {}).get("name", "未知来源")
                    })
                
                return {
                    "success": True,
                    "articles": formatted_articles,
                    "total": data.get("totalArticles", 0),
                    "query": keywords
                }
            else:
                error_msg = f"API请求失败: {response.status_code}"
                try:
                    error_data = response.json()
                    if "errors" in error_data:
                        error_msg = str(error_data.get("errors", {}))
                    else:
                        error_msg = error_data.get("message", error_msg)
                except:
                    pass
                    
                logger.error(f"GNews API 错误: {response.status_code} - {error_msg}")
                
                # 如果是查询语法错误，尝试简化查询
                if response.status_code == 400:
                    simplified_keywords = self._simplify_query(keywords)
                    if simplified_keywords != keywords:
                        logger.info(f"尝试简化查询: {simplified_keywords}")
                        return await self.search_news(simplified_keywords, days_back, max_results)
                
                return {
                    "success": False,
                    "articles": [],
                    "error": error_msg
                }
                
        except Exception as e:
            logger.error(f"新闻搜索失败: {e}")
            return {
                "success": False,
                "articles": [],
                "error": str(e)
            }
    
    def _extract_keywords(self, query: str) -> str:
        """提取搜索关键词"""
        # 移除常见的停用词
        stop_words = [
            "新闻", "最新", "实时", "热点", "今天", "昨天", "明天",
            "报道", "发生了什么", "时事", "要闻", "近期", "最近",
            "新消息", "快讯", "动态", "更新", "有哪些", "什么",
            "告诉", "我", "想", "知道", "了解", "看", "查"
        ]
        
        result = query.lower()
        for word in stop_words:
            result = result.replace(word, "")
        
        # 移除标点符号
        result = re.sub(r'[？?！!。，、；：""''（）【】《》\s]+', ' ', result)
        result = result.strip()
        
        # 如果结果为空或太短，使用默认
        if len(result) < 2:
            return "technology"
        
        # 限制长度
        return result[:30]
    
    def _simplify_query(self, query: str) -> str:
        """简化查询词"""
        # 如果查询包含多个词，只取第一个
        words = query.split()
        if len(words) > 1:
            return words[0]
        return query
    
    def format_news_context(self, news_result: dict) -> str:
        """将新闻格式化为上下文"""
        if not news_result.get("success"):
            return "未能获取到新闻，请稍后再试。"
        
        articles = news_result.get("articles", [])
        if not articles:
            return f"未找到关于「{news_result.get('query', '')}」的相关新闻。"
        
        context = f"【实时新闻检索结果 - 关键词：{news_result.get('query', '')}】\n\n"
        for i, article in enumerate(articles[:5], 1):
            context += f"{i}. **{article['title']}**\n"
            context += f"   来源：{article['source']}\n"
            context += f"   时间：{self._format_date(article['publishedAt'])}\n"
            desc = article['description'][:150] if article['description'] else article['content'][:150] if article['content'] else ""
            if desc:
                context += f"   摘要：{desc}...\n"
            context += f"   链接：{article['url']}\n\n"
        
        context += "请基于以上新闻内容回答用户的问题。如果新闻内容不足以回答，请如实告知用户。"
        return context
    
    def _format_date(self, date_str: str) -> str:
        """格式化日期"""
        if not date_str:
            return "未知时间"
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M")
        except:
            return date_str[:16]

# 全局新闻服务实例
news_service = NewsService()

# ============== 图片生成功能 ==============
async def generate_image(prompt: str, user_id: str) -> tuple:
    """
    生成图片
    返回 (成功标志, 图片URL或错误信息)
    """
    if IMAGE_API_KEY and IMAGE_API_URL:
        try:
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(
                    IMAGE_API_URL,
                    headers={
                        "Authorization": f"Bearer {IMAGE_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "wanx-v1",
                        "input": {"prompt": prompt},
                        "parameters": {"size": "1024*1024", "n": 1}
                    },
                    timeout=60.0
                )
                if response.status_code == 200:
                    data = response.json()
                    image_url = data.get("output", {}).get("results", [{}])[0].get("url")
                    if image_url:
                        return True, image_url
        except Exception as e:
            logger.error(f"图片生成失败: {e}")
    
    # 使用 Unsplash 占位图
    encoded_prompt = requests.utils.quote(prompt[:50])
    placeholder_url = f"https://source.unsplash.com/800x600/?{encoded_prompt}"
    
    return True, placeholder_url

# ============== 文件分析功能 ==============
async def analyze_image(image_data: str, user_question: str = "") -> str:
    """分析图片内容"""
    if not user_question:
        user_question = "请详细描述这张图片的内容，包括看到的物体、场景、颜色和可能传达的信息。"
    
    try:
        response = client.chat.completions.create(
            model=AGENT_CONFIGS["image_analysis"]["model"],
            messages=[
                {"role": "system", "content": AGENT_CONFIGS["image_analysis"]["system_prompt"]},
                {"role": "user", "content": f"{user_question}\n\n[用户上传了一张图片，请根据你的能力进行分析和理解]"}
            ],
            extra_body={"thinking_mode": AGENT_CONFIGS["image_analysis"]["thinking_mode"]}
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"图片分析失败: {e}")
        return f"抱歉，暂时无法分析这张图片。错误信息：{str(e)}"

async def analyze_video(video_data: str, user_question: str = "") -> str:
    """分析视频内容"""
    if not user_question:
        user_question = "请分析这个视频的可能内容，包括场景、主题和相关信息。"
    
    try:
        response = client.chat.completions.create(
            model=AGENT_CONFIGS["video_analysis"]["model"],
            messages=[
                {"role": "system", "content": AGENT_CONFIGS["video_analysis"]["system_prompt"]},
                {"role": "user", "content": f"{user_question}\n\n[用户上传了一个视频，请根据你的能力进行分析]"}
            ],
            extra_body={"thinking_mode": AGENT_CONFIGS["video_analysis"]["thinking_mode"]}
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"视频分析失败: {e}")
        return f"抱歉，暂时无法分析这个视频。错误信息：{str(e)}"

async def analyze_file(file_data: str, file_name: str, user_question: str = "") -> str:
    """分析文档内容"""
    if not user_question:
        user_question = f"请分析文件'{file_name}'的内容，总结要点和关键信息。"
    
    try:
        response = client.chat.completions.create(
            model=AGENT_CONFIGS["file_analysis"]["model"],
            messages=[
                {"role": "system", "content": AGENT_CONFIGS["file_analysis"]["system_prompt"]},
                {"role": "user", "content": f"{user_question}\n\n[用户上传了文件 '{file_name}'，请根据你的能力进行分析]"}
            ],
            extra_body={"thinking_mode": AGENT_CONFIGS["file_analysis"]["thinking_mode"]}
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"文件分析失败: {e}")
        return f"抱歉，暂时无法分析这个文件。错误信息：{str(e)}"

# ============== 新闻处理功能 ==============
async def handle_news_query(user_input: str) -> tuple:
    """
    处理新闻查询
    返回 (回答, 新闻数据列表)
    """
    # 搜索新闻
    news_result = await news_service.search_news(user_input, days_back=3, max_results=6)
    
    if not news_result["success"]:
        error_msg = news_result.get('error', '未知错误')
        if "400" in error_msg or "syntax" in error_msg.lower():
            return "抱歉，新闻搜索服务暂时遇到问题。请尝试更简单的关键词，比如'科技新闻'或'AI新闻'。", []
        return f"新闻检索失败：{error_msg}", []
    
    articles = news_result["articles"]
    if not articles:
        return f"未找到关于「{news_result.get('query', '')}」的相关新闻。建议换个关键词试试，比如'科技'、'AI'、'互联网'等。", []
    
    # 格式化新闻上下文
    news_context = news_service.format_news_context(news_result)
    
    try:
        response = client.chat.completions.create(
            model=AGENT_CONFIGS["news"]["model"],
            messages=[
                {"role": "system", "content": AGENT_CONFIGS["news"]["system_prompt"]},
                {"role": "user", "content": f"用户提问：{user_input}\n\n{news_context}\n\n请基于以上新闻内容回答用户的问题。如果新闻内容不够全面，可以告诉用户搜索结果的摘要。"}
            ],
            extra_body={"thinking_mode": AGENT_CONFIGS["news"]["thinking_mode"]}
        )
        return response.choices[0].message.content.strip(), articles
    except Exception as e:
        logger.error(f"新闻问答生成失败: {e}")
        news_list_text = "以下是相关新闻：\n\n"
        for i, article in enumerate(articles[:3], 1):
            news_list_text += f"{i}. {article['title']}\n"
            news_list_text += f"   来源：{article['source']}\n"
            news_list_text += f"   时间：{article['publishedAt'][:10] if article['publishedAt'] else '未知'}\n"
            news_list_text += f"   链接：{article['url']}\n\n"
        return news_list_text, articles

# ============== 通用对话 ==============
async def general_chat(user_input: str, agent_type: str) -> str:
    """通用对话"""
    config = AGENT_CONFIGS.get(agent_type, AGENT_CONFIGS["default"])
    
    try:
        response = client.chat.completions.create(
            model=config["model"],
            messages=[
                {"role": "system", "content": config["system_prompt"]},
                {"role": "user", "content": user_input}
            ],
            temperature=0.7,
            top_p=1.0,
            extra_body={"thinking_mode": config["thinking_mode"]}
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"对话失败: {e}")
        return f"服务异常：{str(e)}"

# ============== 核心接口 ==============
@app.post("/ai-assistant", response_model=ChatResponse)
async def ai_assistant(req: ChatRequest):
    start_time = time.time()
    
    try:
        user_input = req.user_input
        user_id = req.user_id
        agent_type = req.agent_type
        file_type = req.file_type
        file_data = req.file_data
        file_name = req.file_name
        
        logger.info(f"用户: {user_id}, 指定agent: {agent_type}, 文件类型: {file_type}")
        logger.info(f"输入内容: {user_input[:100]}..." if len(user_input) > 100 else f"输入内容: {user_input}")
        
        # ========== 路由决策 ==========
        if agent_type == "auto" or not agent_type or agent_type == "":
            final_agent = detect_agent(user_input, file_type)
            logger.info(f"自动路由到: {final_agent}")
        else:
            final_agent = agent_type
            logger.info(f"使用指定Agent: {final_agent}")
        
        # ========== 执行对应功能 ==========
        answer = ""
        image_url = None
        news_data = None
        
        # 1. 图片生成
        if final_agent == "image_generate":
            success, result = await generate_image(user_input, user_id)
            if success:
                answer = f"根据你的描述「{user_input}」，我生成了以下图片："
                image_url = result
            else:
                answer = result
        
        # 2. 新闻检索
        elif final_agent == "news":
            answer, news_data = await handle_news_query(user_input)
        
        # 3. 图片分析
        elif final_agent == "image_analysis" and file_data:
            answer = await analyze_image(file_data, user_input)
        
        # 4. 视频分析
        elif final_agent == "video_analysis" and file_data:
            answer = await analyze_video(file_data, user_input)
        
        # 5. 文件分析
        elif final_agent == "file_analysis" and file_data:
            answer = await analyze_file(file_data, file_name or "未知文件", user_input)
        
        # 6. 普通对话
        else:
            answer = await general_chat(user_input, final_agent)
        
        processing_time = time.time() - start_time
        logger.info(f"✅ 处理完成，耗时: {processing_time:.2f}秒，使用agent: {final_agent}")
        
        return ChatResponse(
            code=200,
            answer=answer,
            agent=final_agent,
            image_url=image_url,
            news_data=news_data,
            processing_time=processing_time
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"❌ 请求处理失败: {str(e)}", exc_info=True)
        return ChatResponse(
            code=500,
            answer=f"服务异常：{str(e)}",
            agent="error",
            processing_time=processing_time
        )

# ============== 文件上传接口 ==============
@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    user_question: str = Form("")
):
    """处理实际文件上传"""
    start_time = time.time()
    
    try:
        file_content = await file.read()
        file_name = file.filename
        content_type = file.content_type
        
        logger.info(f"收到文件上传: {file_name}, 类型: {content_type}, 用户: {user_id}")
        
        if content_type and content_type.startswith('image/'):
            agent_type = "image_analysis"
            answer = await analyze_image(base64.b64encode(file_content).decode('utf-8'), user_question)
        elif content_type and content_type.startswith('video/'):
            agent_type = "video_analysis"
            answer = await analyze_video(base64.b64encode(file_content).decode('utf-8'), user_question)
        else:
            agent_type = "file_analysis"
            answer = await analyze_file(base64.b64encode(file_content).decode('utf-8'), file_name, user_question)
        
        processing_time = time.time() - start_time
        
        return {
            "code": 200,
            "answer": answer,
            "agent": agent_type,
            "file_name": file_name,
            "processing_time": processing_time
        }
        
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        return {
            "code": 500,
            "answer": f"文件处理失败：{str(e)}",
            "agent": "error"
        }

# ============== 健康检查 ==============
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ai-assistant-v2"}

@app.get("/api/healthz")
async def healthz():
    from datetime import timezone
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/api/version")
async def version():
    return {"version": "2.0.0"}

# ============== 测试接口 ==============
@app.get("/test/news")
async def test_news(q: str = "科技"):
    """测试新闻检索功能"""
    result = await news_service.search_news(q, days_back=3, max_results=3)
    return result

# ============== 启动 ==============
if __name__ == "__main__":
    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "sk-xxxxxxxx":
        print("⚠️  警告: 请设置正确的 DEEPSEEK_API_KEY 环境变量")
        print("   export DEEPSEEK_API_KEY='your-real-api-key'")
    else:
        print("=" * 50)
        print("✅ DeepSeek-V4 AI助手服务启动中...")
        print("=" * 50)
        print("📋 支持的功能:")
        print("   1. 💬 通用对话 - default")
        print("   2. ❤️ 情绪陪伴 - emotion")
        print("   3. 📚 百科问答 - wiki")
        print("   4. 🎨 创意写作 - create")
        print("   5. 📰 实时新闻 - news (已配置GNews API)")
        print("   6. 🖼️ 图片分析 - image_analysis")
        print("   7. 🎬 视频分析 - video_analysis")
        print("   8. 📄 文件分析 - file_analysis")
        print("   9. 🎨 图片生成 - image_generate")
        print("=" * 50)
        print("🚀 服务地址: http://127.0.0.1:8000")
        print("📡 接口地址: http://127.0.0.1:8000/ai-assistant")
        print("🏥 健康检查: http://127.0.0.1:8000/health")
        print("📰 新闻测试: http://127.0.0.1:8000/test/news?q=科技")
        print("=" * 50)
        
        uvicorn.run(app, host="0.0.0.0", port=8000)