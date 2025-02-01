# 创建应用实例
import sys
import threading
import time
import os
import json
from wxcloudrun import app, download_file, RESOURCES_FOLDER
from wxcloudrun.utils.file_util import loads_json
# 导入views注册路由
import wxcloudrun.views

# 导出应用实例供gunicorn使用
application = app

# 初始化函数
def init_application():
    # 等待2秒确保服务完全启动
    time.sleep(2)
    # 下载文件
    download_file()
    
    # 加载数据到app配置
    json_file_path = os.path.join(RESOURCES_FOLDER, 'rich_fx_flat_v2.json')
    try:
        school_data = loads_json(json_file_path)
        app.config['SCHOOL_DATAS'] = school_data
        print(f"成功加载学校数据，共{len(school_data)}条记录")
    except Exception as e:
        print(f"加载学校数据失败: {str(e)}")

# 启动Flask Web服务
if __name__ == '__main__':
    # 创建初始化线程
    init_thread = threading.Thread(target=init_application)
    init_thread.daemon = True
    init_thread.start()
    
    # 启动服务
    app.run(host=sys.argv[1], port=int(sys.argv[2]), debug=False)
