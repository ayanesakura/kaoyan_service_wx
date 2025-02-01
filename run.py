# 创建应用实例
import sys
import threading
import time
from wxcloudrun import app, download_file

# 初始化函数
def init_application():
    # 等待2秒确保服务完全启动
    time.sleep(2)
    download_file()

# 启动Flask Web服务
if __name__ == '__main__':
    # 创建初始化线程
    init_thread = threading.Thread(target=init_application)
    init_thread.daemon = True
    init_thread.start()
    
    # 启动服务
    app.run(host=sys.argv[1], port=int(sys.argv[2]), debug=False)
