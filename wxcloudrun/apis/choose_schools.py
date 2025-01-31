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

SCHOOL_DATA_PATH = os.path.join(cur_dir, 'resources/rich_fx_flat_v2.json')

SCHOOL_DATAS = loads_json(SCHOOL_DATA_PATH)

city_level_map = {
    '211': set(),
    '985': set(),
    'c9': set(['北京大学', '清华大学', '复旦大学', '上海交通大学', '浙江大学', '南京大学', '中国科学技术大学', '哈尔滨工业大学', '西安交通大学'])
}

for data in SCHOOL_DATAS:
    school_name, is_985, is_211 = data['school_name'], data['is_985'], data['is_211']
    if is_985:
        city_level_map['985'].add(school_name)
    if is_211:
        city_level_map['211'].add(school_name)


def is_target_match(target_info, school_info):
    # 获取目标信息中的各个字段,不存在则为空
    target_school = target_info.get('school', None)
    target_major = target_info.get('major', None)
    target_direction = target_info.get('direction', None)
    target_city = target_info.get('city', None)
    target_province = target_info.get('province', None)
    target_school_level = target_info.get('school_level', None)
    if target_school is not None:
        target_school_flag = target_school == school_info.get('school_name', '')
    else:
        target_school_flag = True

    ## 专业匹配
    if target_major is not None:
        major_flag = target_major == school_info.get('major', '')
    else:
        major_flag = True
    
    ## 方向匹配
    if target_direction is not None:
        direction_flag = target_direction in [d['yjfxmc'] for d in school_info.get('directions', [])] 
    else:
        direction_flag = True
    
    ## 城市和省份匹配
    if target_city is not None and target_province is not None:
        city_or_province_flag = target_city == school_info.get('city', '') and target_province == school_info.get('province', '')
    else:
        city_or_province_flag = True

    ## 学校层次匹配
    if target_school_level is not None:
        school_level_flag = school_info.get('school_name', '') in city_level_map.get(target_school_level.lower(), set())
    else:
        school_level_flag = True
    
    return target_school_flag and major_flag and direction_flag and city_or_province_flag and school_level_flag


def choose_schools():
    request_data = request.get_json()
    user_info, target_info = request_data.get('user_info', {}), request_data.get('target_info', {})
    # print(request_data)
    sort_info = request_data.get('sort_info', [])
    # 检查target_info中是否至少有一个字段有值
    school, major, city, school_level = target_info.get('school'), target_info.get('major'), target_info.get('city'), target_info.get('school_level')
    if not any([school, major, city, school_level]):
        return jsonify({
            'code': 400,
            'message': '目标信息中至少需要填写学校、专业、城市或学校层次其中之一'
        })
    
    target_schools = [s for s in SCHOOL_DATAS if is_target_match(target_info, s)]

    # # 根据sort_info进行排序
    # if sort_info:
    #     target_schools = sorted(target_schools, key=lambda x: [info['sort_key'] for info in sort_info if info['sort_key'] in x])

    return jsonify({
        'code': 200,
        'data': target_schools[:3]
    })


    