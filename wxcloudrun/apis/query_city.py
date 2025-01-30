import os
import sys
sys.path.append(os.getcwd())
from werkzeug.utils import secure_filename
from wxcloudrun.utils.file_util import loads_json
from flask import request, jsonify
from typing import List, Dict
from collections import defaultdict

# 加载城市数据
cur_dir = os.path.dirname(os.path.abspath(__file__))
cur_dir = os.path.dirname(cur_dir)

CITY_DATA_PATH = os.path.join(cur_dir, 'resources/city_2_province.txt')

# 读取并解析城市数据
city_data = {}
try:
    with open(CITY_DATA_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            city, province = line.strip().split('\t')
            city_data[city] = province

except Exception as e:
    print(f"Error loading city data: {e}")
    city_data = {}

def query_city():
    """
    搜索城市接口
    :return: 匹配的城市及其省份列表
    """
    # 从请求中获取搜索关键词
    request_data = request.get_json()
    query = request_data.get('query', '')
    
    if not query:
        return jsonify({
            'code': 400,
            'message': '搜索关键词不能为空'
        })
        
    # 模糊匹配实现
    results = []
    for city, province in city_data.items():
        if query.lower() in city.lower() or query.lower() in province.lower():
            results.append({'province': province, 'city': city})


    if not results:
        return jsonify({
            'code': 404,
            'message': '未找到匹配的城市'
        })
    
    return jsonify(results)
