import sys
sys.path.append('.')

from openai import OpenAI
from typing import Dict, List, Optional, Union, Iterator
from loguru import logger
import time
import os
from tenacity import retry, stop_after_attempt, wait_exponential

class DoubanApiKey:
    API_KEY = '817320d1-d1f7-4013-9fc9-b3cf64a09ecf'  # 替换为你的豆包 API Key

class DoubanApiBaseUrl:
    BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

class DoubanApiModel:
    MODEL_DEEPSEEK_V3 = "ep-20250210164218-4vwqh"  # 豆包模型ID
    MODEL_DEEPSEEK_R1 = "ep-20250210163707-nsscq"  # 豆包模型ID


class DoubanAPI:
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        """初始化豆包 API 客户端"""
        self.api_key = api_key or os.getenv('ARK_API_KEY') or DoubanApiKey.API_KEY
        
        if not self.api_key:
            raise ValueError("API key must be provided")
            
        self.base_url = base_url or DoubanApiBaseUrl.BASE_URL
        self.model = model or DoubanApiModel.MODEL_DEEPSEEK_V3
        
        # 配置OpenAI客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False,
        **kwargs
    ) -> Union[str, Iterator]:
        """发送聊天请求"""
        try:
            logger.debug(f"Sending request with messages: {messages}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                **kwargs
            )
            
            if stream:
                return self._handle_stream_response(response)
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Chat completion failed: {str(e)}")
            logger.exception("Detailed error information:")
            raise
            
    def _handle_stream_response(self, response: Iterator) -> str:
        """处理流式响应"""
        full_content = ""
        try:
            for chunk in response:
                if not chunk.choices:
                    continue
                    
                if hasattr(chunk.choices[0].delta, 'content'):
                    content = chunk.choices[0].delta.content
                    if content:
                        full_content += content
                        logger.debug(f"Received content: {content}")
                        
            return full_content
            
        except Exception as e:
            logger.error(f"Stream handling failed: {str(e)}")
            logger.exception("Detailed error information:")
            raise

    def upload_file(self, file_path: str) -> str:
        """上传文件到豆包
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件ID
        """
        try:
            with open(file_path, 'rb') as file:
                response = self.client.files.create(
                    file=file,
                    purpose='assistants'
                )
                logger.info(f"Successfully uploaded file: {file_path}")
                return response.id
                
        except Exception as e:
            logger.error(f"File upload failed: {str(e)}")
            logger.exception("Detailed error information:")
            raise

def main():
    """示例用法"""
    api = DoubanAPI()
    
    # 系统消息
    system_message = "你是豆包，是由字节跳动开发的 AI 人工智能助手"
    
    # 普通请求示例
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": "常见的十字花科植物有哪些？"}
    ]
    
    try:
        # 普通请求
        print("----- standard request -----")
        response = api.chat_completion(messages)
        print("Response:", response)
        
        # 流式请求
        print("\n----- streaming request -----")
        stream_response = api.chat_completion(messages, stream=True)
        print("Stream Response:", stream_response)
        
        # 文件上传示例
        # file_path = "path/to/your/file.pdf"
        # file_id = api.upload_file(file_path)
        # print(f"\nUploaded file ID: {file_id}")
        
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        logger.exception("Detailed error information:")

if __name__ == "__main__":
    main() 