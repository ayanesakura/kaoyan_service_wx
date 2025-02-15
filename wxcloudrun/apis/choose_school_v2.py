import json
from typing import List, Dict, Any
from loguru import logger
from flask import request, jsonify, current_app
from wxcloudrun.beans.input_models import UserInfo, TargetInfo, SchoolInfo
from wxcloudrun.score_card.location_score_calculator import LocationScoreCalculator
from wxcloudrun.score_card.major_score_calculator import MajorScoreCalculator
from wxcloudrun.apis.choose_schools import SCHOOL_DATAS, load_school_data, city_level_map
from wxcloudrun.score_card.advanced_study_score_calculator import AdvancedStudyScoreCalculator, init_default_values

# 加载就业数据
EMPLOYMENT_DATA = {}
try:
    with open('wxcloudrun/resources/aggregated_employment_data.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            EMPLOYMENT_DATA[data['school_name']] = data['years_data']
    logger.info(f"成功加载 {len(EMPLOYMENT_DATA)} 所学校的就业数据")
    # 初始化默认值
    init_default_values(EMPLOYMENT_DATA)
except Exception as e:
    logger.error(f"加载就业数据失败: {str(e)}")
    logger.exception(e)

def _convert_to_school_info(school_data: Dict) -> SchoolInfo:
    """
    将原始数据转换为SchoolInfo对象
    :param school_data: 原始学校数据
    :return: SchoolInfo对象
    """
    return SchoolInfo(
        school_name=school_data['school_name'],
        school_code=school_data['school_code'],
        is_985=school_data['is_985'],
        is_211=school_data['is_211'],
        departments=school_data['departments'],
        major=school_data['major'],
        major_code=school_data['major_code'],
        blb=school_data.get('blb', []),
        fsx=school_data.get('fsx', []),
        directions=school_data.get('directions', []),
        province=school_data['province'],
        city=school_data['city']
    )

def _filter_schools(target_info: TargetInfo) -> List[SchoolInfo]:
    """
    根据用户目标筛选学校
    :param target_info: 目标信息
    :return: 符合条件的学校列表
    """
    filtered_schools = []
    
    for school_data in SCHOOL_DATAS:
        # 检查学校是否在目标城市列表中
        if target_info.school_cities:
            school_in_target_cities = any(
                city.province == school_data['province'] and 
                city.city == school_data['city']
                for city in target_info.school_cities
            )
            if not school_in_target_cities:
                continue
        
        # 检查专业是否在目标专业列表中
        if target_info.majors:
            if school_data['major'] not in target_info.majors:
                continue
        
        # 检查学校层次是否符合要求
        if target_info.levels:
            school_level_match = False
            school_name = school_data['school_name']
            
            if 'c9' in [level.lower() for level in target_info.levels] and school_name in city_level_map['c9']:
                school_level_match = True
            elif '985' in target_info.levels and school_data['is_985'] == "1":
                school_level_match = True
            elif '211' in target_info.levels and school_data['is_211'] == "1":
                school_level_match = True
            # TODO: 添加双一流判断，需要数据支持
            if not school_level_match:
                continue
        
        # 转换为SchoolInfo对象
        school_info = _convert_to_school_info(school_data)
        filtered_schools.append(school_info)
    
    logger.info(f"筛选出 {len(filtered_schools)} 所符合条件的学校")
    return filtered_schools

def analyze_schools(user_info: UserInfo, target_info: TargetInfo) -> Dict[str, Any]:
    """
    分析学校接口
    :param user_info: 用户信息
    :param target_info: 目标信息
    :return: 分析结果
    """
    try:
        # 获取符合条件的学校
        schools = _filter_schools(target_info)
        if not schools:
            logger.warning("未找到符合条件的学校")
            return {
                "code": 0,
                "data": {
                    "schools": [],
                    "total": 0,
                    "school_details": []  # 修改为列表格式
                },
                "message": "未找到符合条件的学校"
            }
            
        # 初始化评分计算器
        location_calculator = LocationScoreCalculator(user_info, target_info)
        major_calculator = MajorScoreCalculator(user_info, target_info)
        advanced_study_calculator = AdvancedStudyScoreCalculator(user_info, target_info)
        
        # 计算每所学校的评分
        school_scores = []
        school_map = {}  # 用于存储学校得分和对应的SchoolInfo对象
        score_cards = {}  # 用于存储学校的评分卡详情
        
        for school in schools:
            try:
                # 计算地理位置评分
                location_scores = location_calculator.calculate_total_score(school)
                
                # 计算学校专业评分
                major_scores = major_calculator.calculate_total_score(school)
                
                # 计算总分
                total_score = (location_scores["总分"] + major_scores["总分"]) / 2
                
                # 合并评分结果
                school_score = {
                    "school_name": school.school_name,
                    "major_name": school.major,
                    "location_scores": location_scores,
                    "major_scores": major_scores,
                    "total_score": total_score
                }
                
                # 存储评分卡详情
                score_cards[f"{school.school_name}-{school.major}"] = {
                    "location_card": {
                        "scores": location_scores,
                        "details": {
                            "生活成本": location_calculator.calculate_living_cost_score(school),
                            "家乡匹配度": location_calculator.calculate_hometown_match_score(school),
                            "教育资源": location_calculator.calculate_education_resource_score(school),
                            "医疗资源": location_calculator.calculate_medical_resource_score(school),
                            "工作城市匹配度": location_calculator.calculate_work_city_match_score(school)
                        }
                    },
                    "major_card": {
                        "scores": major_scores,
                        "details": {
                            "学校知名度": major_calculator.calculate_school_reputation_score(school),
                            "专业排名": major_calculator.calculate_major_rank_score(school),
                            "学校综合满意度": major_calculator.calculate_school_satisfaction_score(school),
                            "专业综合满意度": major_calculator.calculate_major_satisfaction_score(school)
                        }
                    }
                }
                
                school_scores.append(school_score)
                school_map[f"{school.school_name}-{school.major}"] = (school, total_score)
                
            except Exception as e:
                logger.error(f"计算学校 {school.school_name} 评分时出错: {str(e)}")
                continue
        
        # 按总分排序
        school_scores.sort(key=lambda x: x["total_score"], reverse=True)
        
        # 添加排名
        for i, score in enumerate(school_scores):
            score["rank"] = i + 1
            
        # 获取top3学校的详细信息
        school_details = []  # 修改为列表
        for score in school_scores[:3]:  # 只取前3个
            key = f"{score['school_name']}-{score['major_name']}"
            if key in school_map:
                school_info = school_map[key][0]
                # 将SchoolInfo对象转换为字典，并添加评分卡信息
                school_detail = {
                    "school_name": school_info.school_name,
                    "school_code": school_info.school_code,
                    "is_985": school_info.is_985,
                    "is_211": school_info.is_211,
                    "departments": school_info.departments,
                    "major": school_info.major,
                    "major_code": school_info.major_code,
                    "blb": school_info.blb,
                    "fsx": school_info.fsx,
                    "directions": school_info.directions,
                    "province": school_info.province,
                    "city": school_info.city,
                    # 添加评分卡信息
                    "score_card": score_cards[key],
                    # 添加就业数据
                    "jy": EMPLOYMENT_DATA.get(school_info.school_name, []),
                    # 添加升学评分卡
                    "advanced_study_card": advanced_study_calculator.calculate_total_score(
                        school_info,
                        EMPLOYMENT_DATA.get(school_info.school_name, [])
                    )
                }
                school_details.append(school_detail)
            
        logger.info(f"完成 {len(school_scores)} 所学校的评分计算，获取top3学校")
        
        return {
            "code": 0,
            "data": {
                "schools": school_scores[:3],  # 只返回前3个学校的得分
                "total": len(school_scores),
                "school_details": school_details  # 返回包含评分卡的学校详细信息列表
            },
            "message": "success"
        }
        
    except Exception as e:
        logger.error(f"分析学校时出错: {str(e)}")
        logger.exception(e)
        return {
            "code": -1,
            "data": None,
            "message": str(e)
        }

def choose_schools_v2():
    """处理学校选择请求的接口函数"""
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

        request_data = request.get_json()
        user_info = UserInfo(**request_data['user_info'])
        target_info = TargetInfo(**request_data['target_info'])
        
        return jsonify(analyze_schools(user_info, target_info))
        
    except Exception as e:
        logger.error(f"处理请求时出错: {str(e)}")
        logger.exception(e)
        return jsonify({
            "code": -1,
            "data": None,
            "message": str(e)
        }) 