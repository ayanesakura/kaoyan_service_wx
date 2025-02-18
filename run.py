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
    json_file_path = os.path.join(RESOURCES_FOLDER, 'rich_fx_flat_v2.json')
    
    # 尝试下载文件
    try:
        if not download_file():
            print("下载文件失败")
            return False
    except Exception as e:
        print(f"下载文件出错: {str(e)}")
        return False
    
    # 等待文件就绪
    max_retries = 30  # 最多等待30秒
    retry_count = 0
    
    while retry_count < max_retries:
        if os.path.exists(json_file_path):
            try:
                # 尝试加载数据以验证文件完整性
                school_data = loads_json(json_file_path)
                if not school_data:
                    raise ValueError("加载的数据为空")
                    
                # 验证数据结构
                required_fields = ['school_name', 'is_985', 'is_211']
                if not all(field in school_data[0] for field in required_fields):
                    raise ValueError("数据结构不完整")
                
                # 保存到应用配置
                app.config['SCHOOL_DATAS'] = school_data
                print(f"成功加载学校数据，共{len(school_data)}条记录")
                return True
            except Exception as e:
                print(f"加载数据失败: {str(e)}")
        
        retry_count += 1
        time.sleep(1)  # 等待1秒后重试
    
    print("数据初始化失败")
    return False

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
