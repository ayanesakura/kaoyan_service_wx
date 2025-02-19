from typing import Dict, Optional
from loguru import logger
from flask import request, jsonify, current_app
from wxcloudrun.apis.choose_schools import SCHOOL_DATAS, load_school_data
from wxcloudrun.score_card.advanced_study_score_calculator import EMPLOYMENT_DATA
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
    """获取学校专业详情的接口函数"""
    try:
        # 确保学校数据已加载
        global SCHOOL_DATAS
        if not SCHOOL_DATAS:
            logger.info("学校数据未加载，开始加载数据...")
            if not load_school_data():
                return jsonify({
                    "code": -1,
                    "data": None,
                    "message": "学校数据加载失败"
                })
            SCHOOL_DATAS = current_app.config.get('SCHOOL_DATAS')
            if not SCHOOL_DATAS:
                return jsonify({
                    "code": -1,
                    "data": None,
                    "message": "学校数据未初始化"
                })
            logger.info(f"成功加载 {len(SCHOOL_DATAS)} 条学校数据")

        # 获取请求参数
        request_data = request.get_json()
        school_name = request_data.get('school_name')
        major_name = request_data.get('major_name')

        # 参数验证
        if not school_name or not major_name:
            return jsonify({
                "code": -1,
                "data": None,
                "message": "缺少必要参数"
            })

        # 查找学校专业
        school_info = _find_school_major(school_name, major_name)
        if not school_info:
            return jsonify({
                "code": -1,
                "data": None,
                "message": "未找到对应的学校专业"
            })

        # 直接返回字典数据
        return jsonify({
            "code": 0,
            "data": school_info,
            "message": "success"
        })

    except Exception as e:
        logger.error(f"获取学校专业详情时出错: {str(e)}")
        logger.exception(e)
        return jsonify({
            "code": -1,
            "data": None,
            "message": str(e)
        })