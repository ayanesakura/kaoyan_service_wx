# 创建应用实例
import sys
import threading
from wxcloudrun import app, download_file

# 启动Flask Web服务
if __name__ == '__main__':
    # 在后台线程中下载文件
    threading.Thread(target=download_file, daemon=True).start()
    # 启动服务
    app.run(host=sys.argv[1], port=sys.argv[2])
