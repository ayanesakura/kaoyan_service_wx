# 创建应用实例
import sys
import threading
import time
import os
import json
from wxcloudrun import app, download_file, init_application, is_data_ready, RESOURCES_FOLDER
from wxcloudrun.utils.file_util import loads_json

def init_data():
    """初始化数据，下载并加载必要的文件"""
    # 调用应用初始化
    print("初始化应用")
    if not init_application():
        print("应用初始化失败")
        return False
    print("应用初始化成功")
    # 验证数据是否准备就绪
    if not is_data_ready():
        print("数据未准备就绪")
        return False
        
    print(f"成功加载学校数据，共{len(app.config['SCHOOL_DATAS'])}条记录")
    return True

# 在导入views之前初始化数据
if not init_data():
    print("关键数据初始化失败，应用无法正常工作")
    sys.exit(1)  # 退出程序

# 导入views注册路由
import wxcloudrun.views

# 导出应用实例供gunicorn使用
application = app

# 启动Flask Web服务
if __name__ == '__main__':
    app.run(host=sys.argv[1], port=int(sys.argv[2]), debug=False)
