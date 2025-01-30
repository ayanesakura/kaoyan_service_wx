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

def query_majors_or_fxs():
    request_data = request.get_json()
    query = request_data.get('query', '')
    if not query:
        return jsonify({
            'code': 400,
            'message': '查询关键词不能为空'
        })
    
    datas = []
    saw = set()
    for data in SCHOOL_DATAS:
        if query in data['专业名称'] or query in data['方向名称']:
            uniq_key = f"{data['专业名称']}-{data['方向名称']}"
            if uniq_key not in saw:
                datas.append({'collage_name': data['院系名称'], 'major_name': data['专业名称'], 'fx_name': data['方向名称']})
            saw.add(uniq_key)
    return jsonify(datas)
