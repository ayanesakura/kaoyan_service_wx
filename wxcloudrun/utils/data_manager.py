import os
import time
import requests
import threading
from loguru import logger
from typing import Optional, Dict, List
import sys
import os
sys.path.append(os.getcwd())


class DataManager:
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DataManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self.resources_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resources')
                    self.school_data_file = os.path.join(self.resources_dir, 'rich_fx_flat_v2.json')
                    self.school_data = None
                    self._initialized = True
    
    def get_access_token(self) -> Optional[str]:
        """获取微信云开发access token"""
        try:
            appid = "wx81019c53b1467685"
            secret = "c44a45f3c236cb978a0a25e1767a51fc"
            
            url = f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={appid}&secret={secret}'
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"获取access_token失败: {response.text}")
                return None
                
            result = response.json()
            if 'access_token' not in result:
                logger.error(f"获取access_token失败: {result}")
                return None
                
            logger.info("成功获取access_token")
            return result['access_token']
            
        except Exception as e:
            logger.error(f"获取access_token时出错: {str(e)}")
            return None
    
    def download_file(self) -> bool:
        """下载学校数据文件"""
        try:
            # 确保资源目录存在
            os.makedirs(self.resources_dir, exist_ok=True)
            
            # 如果文件已存在且非空，直接返回成功
            if os.path.exists(self.school_data_file) and os.path.getsize(self.school_data_file) > 0:
                logger.info(f"学校数据文件已存在: {self.school_data_file}")
                return True
            
            # 获取access_token
            access_token = self.get_access_token()
            if not access_token:
                return False
            
            # 获取下载URL
            url = "https://api.weixin.qq.com/tcb/batchdownloadfile"
            data = {
                "env": "prod-4g46sjwd41c4097c",
                "file_list": [
                    {
                        "fileid": "cloud://prod-4g46sjwd41c4097c.7072-prod-4g46sjwd41c4097c-1330319089/rich_fx_flat_v2.json",
                        "max_age": 7200
                    }
                ]
            }
            
            headers = {'Content-Type': 'application/json'}
            response = requests.post(
                f"{url}?access_token={access_token}",
                headers=headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('errcode') != 0:
                logger.error(f"获取下载URL失败: {result.get('errmsg')}")
                return False
            
            # 下载文件
            file_list = result.get('file_list', [])
            if not file_list:
                logger.error("文件列表为空")
                return False
            
            download_url = file_list[0].get('download_url')
            if not download_url:
                logger.error("下载URL为空")
                return False
            
            file_response = requests.get(download_url, timeout=30)
            file_response.raise_for_status()
            
            # 保存文件
            with open(self.school_data_file, 'wb') as f:
                f.write(file_response.content)
            
            # 验证文件
            if not os.path.exists(self.school_data_file) or os.path.getsize(self.school_data_file) == 0:
                logger.error("文件下载失败或文件为空")
                return False
            
            logger.info(f"成功下载学校数据文件: {self.school_data_file}")
            return True
            
        except Exception as e:
            logger.error(f"下载文件时出错: {str(e)}")
            return False
    
    
    def initialize(self, max_retries: int = 1) -> bool:
        """初始化数据管理器"""
        retry_count = 0
        while retry_count < max_retries:
            try:
                logger.info(f"开始初始化数据 (第 {retry_count + 1} 次尝试)")
                
                # 下载文件
                if not self.download_file():
                    raise Exception("下载文件失败")
                
                logger.info("下载数据成功")
                return True
                
            except Exception as e:
                logger.error(f"初始化失败: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"等待5秒后重试...")
                    time.sleep(5)
        
        logger.error(f"在 {max_retries} 次尝试后仍然无法初始化数据")
        return False
    

# 创建全局单例实例
data_manager = DataManager() 
data_manager.initialize()