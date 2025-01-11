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
SCHOOL_DATA_PATH = os.path.join(cur_dir, 'resources/全部学校信息.json')
# 加载专业详细数据
MAJOR_DATA_PATH = os.path.join(cur_dir, 'resources/all_major_detail.json')

schools = loads_json(SCHOOL_DATA_PATH)
schools = [school['学校名称'] for school in schools]

# 加载并预处理专业数据
major_data = loads_json(MAJOR_DATA_PATH)
school_structure = {}

# 构建学校-学院-专业的层级结构
for item in major_data:
    school = item['dwmc']
    college = item['yxsmc']
    major = item['zymc']
    
    if school not in school_structure:
        school_structure[school] = {}
    
    if college not in school_structure[school]:
        school_structure[school][college] = []
        
    if major not in school_structure[school][college]:
        school_structure[school][college].append(major)


def search_schools():
    """
    搜索学校接口
    :return: 匹配的学校列表
    """
    # 从请求中获取搜索关键词
    request_data = request.get_json()
    query = request_data.get('query', '')
    
    if not query:
        return jsonify({
            'code': 400,
            'message': '搜索关键词不能为空'
        }), 400
        
    # 简单的模糊匹配实现
    results = []
    for school in schools:
        if query.lower() in str(school).lower():
            results.append(school)
    results = [{'name': i} for i in results]
    
    return jsonify(results)


def get_school_structure():
    """
    获取学校的学院和专业结构
    :param school_name: 学校名称
    :return: 包含学院和专业信息的字典
    """
    request_data = request.get_json()
    school_name = request_data.get('school_name', '')
    if not school_name:
        return jsonify({
            'code': 400,
            'message': '学校名称不能为空'
        }), 400
        
    if school_name not in school_structure:
        return jsonify({
            'code': 404,
            'message': '未找到该学校信息'
        }), 404
    
    result = {
        "school": school_name,
        "colleges": [
            {
                "name": college,
                "majors": majors
            }
            for college, majors in school_structure[school_name].items()
        ]
    }
    
    return jsonify(result)