# 创建应用实例
import sys
from wxcloudrun import app, download_file

# 启动Flask Web服务
if __name__ == '__main__':
    # 先下载文件
    download_file()
    # 启动服务
    app.run(host=sys.argv[1], port=sys.argv[2])
