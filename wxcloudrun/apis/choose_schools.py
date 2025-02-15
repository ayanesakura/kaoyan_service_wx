import os
import sys
sys.path.append(os.getcwd())
from werkzeug.utils import secure_filename
from wxcloudrun.utils.file_util import loads_json
from flask import request, jsonify, current_app
from typing import List, Dict
import time
from wxcloudrun.utils.admission_score_card import get_admission_score
import math

# 加载学校基础数据
cur_dir = os.path.dirname(os.path.abspath(__file__))
cur_dir = os.path.dirname(cur_dir)

SCHOOL_DATA_PATH = os.path.join(cur_dir, 'resources/rich_fx_flat_v2.json')

# 全局变量存储数据
SCHOOL_DATAS = None
city_level_map = {
    '211': set(),
    '985': set(),
    'c9': set(['北京大学', '清华大学', '复旦大学', '上海交通大学', '浙江大学', '南京大学', '中国科学技术大学', '哈尔滨工业大学', '西安交通大学'])
}

def load_school_data():
    """加载学校数据，如果文件不存在则等待并重试"""
    global SCHOOL_DATAS, city_level_map
    
    max_retries = 30  # 最多等待30秒
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            if os.path.exists(SCHOOL_DATA_PATH):
                SCHOOL_DATAS = loads_json(SCHOOL_DATA_PATH)
                # 更新city_level_map
                for data in SCHOOL_DATAS:
                    school_name, is_985, is_211 = data['school_name'], data['is_985'], data['is_211']
                    if is_985 == "1":
                        city_level_map['985'].add(school_name)
                    if is_211 == "1":
                        city_level_map['211'].add(school_name)
                return True
        except Exception as e:
            print(f"Error loading school data: {e}")
        
        retry_count += 1
        time.sleep(1)  # 等待1秒后重试
    
    return False

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

def calculate_admission_probability(score: float) -> float:
    """
    使用 Logistic 函数计算录取概率
    P = 1 / (1 + e^(-0.1 * (S - 65)))
    
    :param score: 评分卡总分
    :return: 录取概率（0-1之间的浮点数）
    """
    try:
        return 1 / (1 + math.exp(-0.1 * (score - 65)))
    except:
        return 0

def choose_schools():
    global SCHOOL_DATAS
    # 从应用配置中获取数据
    SCHOOL_DATAS = current_app.config.get('SCHOOL_DATAS')
    if not SCHOOL_DATAS:
        return jsonify({
            'code': 500,
            'message': '学校数据未初始化，请稍后重试'
        })

    request_data = request.get_json()
    user_info, target_info = request_data.get('user_info', {}), request_data.get('target_info', {})
    sort_info = request_data.get('sort_info', [])
    
    # 检查target_info中是否至少有一个字段有值
    school, major, city, school_level = target_info.get('school'), target_info.get('major'), target_info.get('city'), target_info.get('school_level')
    if not any([school, major, city, school_level]):
        return jsonify({
            'code': 400,
            'message': '目标信息中至少需要填写学校、专业、城市或学校层次其中之一'
        })
    
    target_schools = [s for s in SCHOOL_DATAS if is_target_match(target_info, s)]

    # 计算每个学校的评分和录取概率
    for school in target_schools:
        if 'fxs' in school:
            school.pop('fsx')
        scores = get_admission_score(user_info, target_info, school)
        total_score = scores["总分"]  # 从返回的字典中获取总分
        probability = calculate_admission_probability(total_score)
        school['scores'] = scores  # 保存所有维度的分数
        school['admission_probability'] = round(probability * 100, 2)  # 转换为百分比并保留两位小数
    
    # 按照录取概率降序排序
    target_schools.sort(key=lambda x: x['admission_probability'], reverse=True)

    return jsonify({
        'code': 200,
        'data': target_schools[:5]
    })


    