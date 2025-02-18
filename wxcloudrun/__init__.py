from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import pymysql
import config
import os
import sys
import logging
import json
import requests
import time
from wxcloudrun.utils.file_util import loads_json
from wxcloudrun.utils.token_manager import token_manager
# 因MySQLDB不支持Python3，使用pymysql扩展库代替MySQLDB库
pymysql.install_as_MySQLdb()

# 配置日志
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger()

# 初始化web应用
app = Flask(__name__, instance_relative_config=True)

# 加载配置
app.config.from_object('config')

# 设置SQLAlchemy配置
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 确保resources目录存在
RESOURCES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')
os.makedirs(RESOURCES_FOLDER, exist_ok=True)

# 设定数据库链接
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://{}:{}@{}/flask_demo'.format(config.username, config.password,
                                                                             config.db_address)

# 初始化DB操作对象
db = SQLAlchemy(app)

# 缓存access_token
_access_token = None
_access_token_expires = 0

def get_access_token():
    global _access_token, _access_token_expires
    
    # 如果缓存的token还有30分钟以上的有效期，直接返回
    if _access_token and time.time() + 1800 < _access_token_expires:
        return _access_token
        
    try:
        # 从环境变量获取appid和secret
        appid = "wx81019c53b1467685"
        secret = "c44a45f3c236cb978a0a25e1767a51fc"
        
            
        # 请求access_token
        url = f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={appid}&secret={secret}'
        response = requests.get(url)
        
        if response.status_code != 200:
            logger.error(f"Failed to get access_token: {response.text}")
            return None
            
        result = response.json()
        if 'access_token' not in result:
            logger.error(f"Failed to get access_token: {result}")
            return None
            
        # 更新缓存
        _access_token = result['access_token']

        logger.info("Successfully got new access_token")
        return _access_token
        
    except Exception as e:
        logger.error(f"Failed to get access_token: {str(e)}")
        return None

def download_file():
    """下载文件"""
    # 确保资源目录存在
    if not os.path.exists(RESOURCES_FOLDER):
        os.makedirs(RESOURCES_FOLDER)
    file_path = os.path.join(RESOURCES_FOLDER, 'rich_fx_flat_v2.json')
    if os.path.exists(file_path):
        return True
        
    try:
        # 获取access_token
        success, token_or_error = token_manager.get_access_token()
        if not success:
            logger.error(f"Failed to get access_token: {token_or_error}")
            return False
            
        access_token = token_or_error
        
        # 构建下载请求
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
        if result.get('errcode') == 0:
            file_list = result.get('file_list', [])
            if file_list:
                download_url = file_list[0].get('download_url')
                if download_url:
                    # 下载文件
                    file_response = requests.get(download_url, timeout=30)
                    file_response.raise_for_status()
                    
                    # 保存文件
                    with open(file_path, 'wb') as f:
                        f.write(file_response.content)
                    logger.info(f"Successfully downloaded file to {file_path}")
                    return True
                else:
                    logger.error("No download URL in response")
            else:
                logger.error("No files in response")
        else:
            logger.error(f"Failed to get download URL: {result.get('errmsg', 'Unknown error')}")
        
        return False
        
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return False

def init_application():
    time.sleep(2)
    download_file()  # 文件下载
    # 加载数据到配置
    json_file_path = os.path.join(RESOURCES_FOLDER, 'rich_fx_flat_v2.json')
    
    # 等待文件真正存在
    max_retries = 10
    retry_count = 0
    while not os.path.exists(json_file_path) and retry_count < max_retries:
        time.sleep(1)
        retry_count += 1
        
    # 只有在文件存在时才进行数据加载
    if os.path.exists(json_file_path):
        try:
            school_data = loads_json(json_file_path)
            app.config['SCHOOL_DATAS'] = school_data
        except Exception as e:
            logger.error(f"加载学校数据失败: {str(e)}")

def is_data_ready():
    return bool(app.config.get('SCHOOL_DATAS'))

def choose_schools_v2():
    if not is_data_ready():
        return jsonify({
            "code": -1,
            "message": "系统初始化中,请稍后重试"
        })
