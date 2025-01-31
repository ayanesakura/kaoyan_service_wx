import os
import sys
sys.path.append(os.getcwd())
from werkzeug.utils import secure_filename
from wxcloudrun.utils.file_util import loads_json
from flask import request, jsonify
from typing import List, Dict
from wxcloudrun.utils.kimi_api_utils import KimiApiClient


kimi_client = KimiApiClient()


def ai_ana():
    request_data = request.get_json()
    user_info, target_info = request_data.get('user_info', {}), request_data.get('target_info', {})
    sort_info = request_data.get('sort_info', [])
    sort_info.sort(key=lambda x: -x['weight'])

    sort_str = '' if  len(sort_info) == 0  else '、'.join([info['name'] for info in sort_info])
    prompt = [
        '## 角色',
        '你是一个资深的考研择校咨询师，你擅长发现学生的特点，结合他们的需求，给出合适的择校建议',
        '## 学生基本信息',
        f'学校：{user_info.get("school", "")}',
        f'专业：{user_info.get("major", "")}',
        f'年级：{user_info.get("grade", "")}',
        f'当前专业排名：{user_info.get("rank", "")}',
        f'是否一战：{user_info.get("is_first_time", "")}',
        f'擅长的科目：{user_info.get("good_subject", "")}',
        '## 目标院校信息',
        f'专业：{target_info.get("major", "")}',
        f'期望城市：{target_info.get("city", "")}',
        f'学校要求：{target_info.get("school_level", "")}',
        f'择校优先级：{sort_str}'
    ]
    prompt = '\n'.join(prompt)
    max_retry_times, idx = 3, 0
    
    while idx < max_retry_times:
        try:
            response = kimi_client.run_kimi_api(prompt)
            break
        except Exception as e:
            idx += 1
    return jsonify({
        'code': 200,
        'data': {
            'content': response
        }
    })


