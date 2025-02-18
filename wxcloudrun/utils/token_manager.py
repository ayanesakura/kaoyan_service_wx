import os
import time
import json
import threading
from typing import Optional, Tuple
import requests
from loguru import logger

class TokenManager:
    """Token管理器单例类"""
    _instance = None
    _lock = threading.Lock()
    _token_lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(TokenManager, cls).__new__(cls)
                    cls._instance._init_manager()
        return cls._instance
    
    def _init_manager(self):
        """初始化管理器"""
        self._access_token = None
        self._token_expires_at = 0
        self._last_token_request = 0
        self._min_request_interval = 60  # 最小请求间隔(秒)
        
        # 从环境变量获取配置
        self._appid = os.getenv('APPID', 'wx81019c53b1467685')
        self._secret = os.getenv('SECRET', 'c44a45f3c236cb978a0a25e1767a51fc')
        
    def get_access_token(self) -> Tuple[bool, str]:
        """
        获取access_token，确保在1分钟内不会重复请求
        返回: (是否成功, token或错误信息)
        """
        current_time = time.time()
        
        # 检查是否需要刷新token
        if self._access_token and current_time < self._token_expires_at:
            return True, self._access_token
            
        # 检查是否满足最小请求间隔
        if current_time - self._last_token_request < self._min_request_interval:
            if self._access_token:  # 如果还有旧token，继续使用
                return True, self._access_token
            return False, "请求过于频繁，请稍后再试"
        
        # 使用锁确保并发安全
        with self._token_lock:
            # 双重检查，避免其他线程已经刷新了token
            if self._access_token and current_time < self._token_expires_at:
                return True, self._access_token
                
            # 再次检查请求间隔
            if current_time - self._last_token_request < self._min_request_interval:
                if self._access_token:
                    return True, self._access_token
                return False, "请求过于频繁，请稍后再试"
            
            try:
                # 更新最后请求时间
                self._last_token_request = current_time
                
                # 请求新token
                url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={self._appid}&secret={self._secret}"
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                if 'access_token' in result:
                    self._access_token = result['access_token']
                    self._token_expires_at = current_time + result.get('expires_in', 7200) - 300  # 提前5分钟过期
                    logger.info(f"Successfully got new access_token: {self._access_token}")
                    return True, self._access_token
                else:
                    error_msg = f"Failed to get access_token: {result.get('errmsg', 'Unknown error')}"
                    logger.error(error_msg)
                    return False, error_msg
                    
            except Exception as e:
                error_msg = f"Error getting access_token: {str(e)}"
                logger.error(error_msg)
                return False, error_msg

# 创建全局单例实例
token_manager = TokenManager() 