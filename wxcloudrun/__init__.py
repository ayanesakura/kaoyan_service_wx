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