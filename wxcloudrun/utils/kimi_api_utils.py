from pathlib import Path
from openai import OpenAI
 

class KimiApiKey:
    MOONSHOT_API_KEY = 'sk-AAjyl0V4QQ4jik0VpY5lWaz3Y1cQHLLtAKaVVGUeW6bZSNRW'


class KimiApiBaseUrl:
    BASE_URL = "https://api.moonshot.cn/v1"

class KimiApiModel:
    MODEL_v1_32k = "moonshot-v1-32k"
    MODEL_v1_8k = "moonshot-v1-8k"

class KimiApiClient:
    def __init__(self, api_key=KimiApiKey.MOONSHOT_API_KEY, base_url=KimiApiBaseUrl.BASE_URL, model=KimiApiModel.MODEL_v1_32k):
        self.client = OpenAI(
            api_key=api_key, # 在这里将 MOONSHOT_API_KEY 替换为你从 Kimi 开放平台申请的 API Key
            base_url=base_url
        )
        self.model = model
    
    def get_file_content(self, file_path):
        file_object = self.client.files.create(file=Path(file_path), purpose="file-extract")
        try:
            file_content = self.client.files.content(file_id=file_object.id).text
            return file_content
        finally:
            # 获取内容后立即删除文件，避免累积
            self.client.files.delete(file_id=file_object.id)
    
    def run_kimi_api(self, prompt, file_path: str = None, temperature=1.0):
        if file_path:
            file_content = self.get_file_content(file_path)
            messages = [
                {
                    "role": "system",
                "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一切涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
                },
                 {"role": "system", "content": file_content},
                {"role": "user", "content": prompt},
            ]
        else:
            messages = [
                {
                    "role": "system",
                    "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一切涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
                },
                {"role": "user", "content": prompt}
            ]
        print(messages)

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature
        )
        return completion.choices[0].message.content
