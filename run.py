# 创建应用实例
import sys
from wxcloudrun import app

# 导出应用实例供gunicorn使用
application = app

# 启动Flask Web服务
if __name__ == '__main__':
    # 启动服务
    print("fuck")
    app.run(host=sys.argv[1], port=sys.argv[2])
