from typing import Dict, Optional
from loguru import logger
from flask import request, jsonify, current_app
from utils.file_util import SCHOOL_DATAS
from wxcloudrun.utils.file_util import EMPLOYMENT_DATA
from wxcloudrun.beans.input_models import SchoolInfo

def _find_school_major(school_name: str, major_name: str) -> Optional[Dict]:
    """
    根据学校名称和专业名称查找对应的学校数据
    """
    try:
        # 遍历所有学校数据
        for school in SCHOOL_DATAS:
            if school.get('school_name') == school_name and school.get('major') == major_name:
                # 获取就业数据
                employment_info = EMPLOYMENT_DATA.get(school_name, [])
                # 将就业数据添加到学校信息中
                school_data = dict(school)  # 创建副本避免修改原始数据
                school_data['jy'] = employment_info
                return school_data
        return None
    except Exception as e:
        logger.error(f"查找学校专业时出错: {str(e)}")
        return None

def get_school_detail():
    """获取学校详情"""
    try:
        # 获取请求参数
        data = request.get_json()
        school_name = data.get('school_name')
        
        if not school_name:
            return jsonify({
                'code': 400,
                'message': '缺少学校名称参数'
            })
        
        # 获取学校就业数据
        employment_info = EMPLOYMENT_DATA.get(school_name, [])
        
        # 返回结果
        return jsonify({
            'code': 0,
            'data': {
                'school_name': school_name,
                'employment_data': employment_info
            }
        })
    except Exception as e:
        logger.error(f"获取学校详情时出错: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'获取学校详情失败: {str(e)}'
        })