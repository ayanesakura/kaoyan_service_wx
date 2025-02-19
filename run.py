# 创建应用实例
import sys
import threading
import time
import os
import json
from wxcloudrun.utils.data_manager import data_manager


# 启动Flask Web服务
if __name__ == '__main__':
    # 启动服务
    data_manager.initialize()
    from wxcloudrun import app
    # 导入views注册路由
    import wxcloudrun.views

    # 导出应用实例供gunicorn使用
    application = app
    app.run(host=sys.argv[1], port=int(sys.argv[2]), debug=False, threaded=False)
