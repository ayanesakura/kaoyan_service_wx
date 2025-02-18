# 创建应用实例
import sys
import threading
import time
import os
import json
from wxcloudrun import app, download_file, RESOURCES_FOLDER
from wxcloudrun.utils.file_util import loads_json

def init_data():
    """初始化数据，下载并加载必要的文件"""
    # 下载文件并等待完成
    download_file()
    
    # 等待文件下载完成
    json_file_path = os.path.join(RESOURCES_FOLDER, 'rich_fx_flat_v2.json')
    max_retries = 30  # 最多等待30秒
    retry_count = 0
    
    while retry_count < max_retries:
        if os.path.exists(json_file_path):
            try:
                # 尝试加载数据以验证文件完整性
                school_data = loads_json(json_file_path)
                app.config['SCHOOL_DATAS'] = school_data
                print(f"成功加载学校数据，共{len(school_data)}条记录")
                return True  # 成功加载后返回
            except Exception as e:
                print(f"加载学校数据失败: {str(e)}")
        
        retry_count += 1
        time.sleep(1)  # 等待1秒后重试
    
    print("等待文件下载超时")
    return False

# 在导入views之前初始化数据
if init_data():
    # 导入views注册路由
    import wxcloudrun.views
else:
    print("数据初始化失败，应用可能无法正常工作")
    import wxcloudrun.views

# 导出应用实例供gunicorn使用
application = app

# 启动Flask Web服务
if __name__ == '__main__':
    app.run(host=sys.argv[1], port=int(sys.argv[2]), debug=False)
