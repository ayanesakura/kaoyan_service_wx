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
    try:
        # 获取access_token
        pid = os.getpid()
        access_token = get_access_token()
        print(access_token)
        if not access_token:
            logger.error("Failed to get access_token")
            return

        # 调用微信云托管开放接口获取文件下载链接
        api_url = 'https://api.weixin.qq.com/tcb/batchdownloadfile'
        env = "prod-4g46sjwd41c4097c"  # 使用完整的云环境ID
        
        data = {
            "env": env,
            "file_list": [
                {
                    "fileid": f"cloud://prod-4g46sjwd41c4097c.7072-prod-4g46sjwd41c4097c-1330319089/rich_fx_flat_v2.json",  # 使用正确格式的文件ID
                    "max_age": 7200
                }
            ]
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        logger.info(f"Requesting download url with data: {data}")  # 添加日志
        
        # 使用access_token调用接口
        response = requests.post(
            f"{api_url}?access_token={access_token}",
            json=data,
            headers=headers
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to get download url: {response.text}")
            return
            
        result = response.json()
        if result.get('errcode') != 0:
            logger.error(f"Failed to get download url: {result}")
            return
            
        # 获取下载链接
        file_list = result.get('file_list', [])
        if not file_list:
            logger.error("No download url returned")
            return
            
        download_url = file_list[0].get('download_url', '')
        if not download_url:
            logger.error("Download url is empty")
            return
            
        # 下载文件
        file_response = requests.get(download_url)
        if file_response.status_code != 200:
            logger.error(f"Failed to download file: {file_response.text}")
            return
            
        # 保存文件
        local_file_path = os.path.join(RESOURCES_FOLDER, 'rich_fx_flat_v2.json')
        with open(local_file_path, 'wb') as f:
            f.write(file_response.content)
            
        logger.info(f"Successfully downloaded file to {local_file_path}, process id: {pid}")
    except Exception as e:
        logger.error(f"Failed to download file: {str(e)}")

def init_data():
    # 检查文件是否存在
    local_file_path = os.path.join(RESOURCES_FOLDER, 'rich_fx_flat_v2.json')
    if os.path.exists(local_file_path):
        try:
            app.config['SCHOOL_DATAS'] = loads_json(local_file_path)
            logger.info(f"Successfully loaded existing school data, process id: {os.getpid()}")
            return
        except Exception as e:
            logger.error(f"Failed to load existing school data: {str(e)}")
    
    # 如果文件不存在或加载失败，则下载
    download_file()
