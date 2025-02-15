from pathlib import Path
from openai import OpenAI
import httpx
import logging
import traceback

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeepSeekApiKey:
    DEEPSEEK_API_KEY = 'sk-af1f648aaa43495f8b409ea80187699e'  # 替换为你的 API Key

class DeepSeekApiBaseUrl:
    BASE_URL = "https://api.deepseek.com/v1"

class DeepSeekApiModel:
    MODEL_CHAT = "deepseek-chat"
    MODEL_REASONER = "deepseek-reasoner"

class DeepSeekApiClient:
    def __init__(self, api_key=DeepSeekApiKey.DEEPSEEK_API_KEY, 
                 base_url=DeepSeekApiBaseUrl.BASE_URL, 
                 model=DeepSeekApiModel.MODEL_CHAT,
                 timeout=30):
        logger.info(f"初始化 DeepSeek 客户端: model={model}, timeout={timeout}")
        try:
            self.client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                http_client=httpx.Client(timeout=timeout)
            )
            self.model = model
            logger.info("DeepSeek 客户端初始化成功")
        except Exception as e:
            logger.error(f"DeepSeek 客户端初始化失败: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def run_deepseek_api(self, prompt, temperature=1.0):
        logger.info(f"开始调用 DeepSeek API: model={self.model}, temperature={temperature}")
        logger.info(f"Prompt: {prompt[:200]}...")  # 只记录前200个字符

        messages = [
            {
                "role": "system",
                "content": "你是 DeepSeek AI 提供的智能助手。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一切涉及恐怖主义，种族歧视，黄色暴力等问题的回答。",
            },
            {"role": "user", "content": prompt}
        ]

        try:
            logger.info("发送请求到 DeepSeek API...")
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=False
            )
            response = completion.choices[0].message.content
            logger.info(f"DeepSeek API 调用成功，响应长度: {len(response)}")
            return response
            
        except httpx.TimeoutException as e:
            logger.error(f"DeepSeek API 请求超时: {str(e)}")
            return "请求超时，请稍后重试"
        except Exception as e:
            logger.error(f"DeepSeek API 调用失败: {str(e)}")
            logger.error(traceback.format_exc())
            raise
