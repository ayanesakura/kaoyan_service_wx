import os
import sys
sys.path.append(os.getcwd())
from werkzeug.utils import secure_filename
from wxcloudrun.utils.file_util import loads_json
from flask import request, jsonify
from typing import List, Dict

# 加载学校基础数据
cur_dir = os.path.dirname(os.path.abspath(__file__))
cur_dir = os.path.dirname(cur_dir)

SCHOOL_DATA_PATH = os.path.join(cur_dir, 'resources/fx_flat.json')

SCHOOL_DATAS = loads_json(SCHOOL_DATA_PATH)

def query_school_majors_or_fxs():
    request_data = request.get_json()
    school_name, query = request_data.get('school', ''), request_data.get('query', '')
    if not school_name or not query:
        return jsonify({
            'code': 400,
            'message': '学校名称和查询关键词不能为空'
        })
    
    datas = [{'collage_name': data['院系名称'], 'major': data['专业名称'], 'fx': data['方向名称']} 
             for data in SCHOOL_DATAS if data['学校名称'] == school_name and (query in data['专业名称'] or query in data['方向名称'])]
    if not datas:
        return jsonify({
            'code': 404,
            'message': '未找到该学校信息'
        })
    
    return jsonify(datas)



