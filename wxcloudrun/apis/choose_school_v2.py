import json
from typing import List, Dict, Any
from loguru import logger
from flask import request, jsonify, current_app
from wxcloudrun.beans.input_models import UserInfo, TargetInfo, SchoolInfo, Area
from wxcloudrun.score_card.admission_score_calculator import AdmissionScoreCalculator
from wxcloudrun.score_card.location_score_calculator import LocationScoreCalculator
from wxcloudrun.score_card.major_score_calculator import MajorScoreCalculator
from wxcloudrun.score_card.constants import PROBABILITY_LEVELS, SCORE_CARD_WEIGHTS
from wxcloudrun.apis.choose_schools import SCHOOL_DATAS, load_school_data, city_level_map
from wxcloudrun.score_card.advanced_study_score_calculator import AdvancedStudyScoreCalculator, init_default_values

# 初始化全局变量
if SCHOOL_DATAS is None:
    SCHOOL_DATAS = []

# 确保学校数据已加载
if len(SCHOOL_DATAS) == 0:
    logger.info("学校数据未加载，开始加载数据...")
    try:
        if load_school_data():
            SCHOOL_DATAS = current_app.config.get('SCHOOL_DATAS', [])
            logger.info(f"成功加载 {len(SCHOOL_DATAS)} 条学校数据")
        else:
            logger.error("学校数据加载失败")
            SCHOOL_DATAS = []
    except Exception as e:
        logger.error(f"加载学校数据时出错: {str(e)}")
        logger.exception(e)
        SCHOOL_DATAS = []

# 加载就业数据
EMPLOYMENT_DATA = {}
try:
    with open('wxcloudrun/resources/aggregated_employment_data.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
                EMPLOYMENT_DATA[data['school_name']] = data['years_data']
            except json.JSONDecodeError as e:
                logger.error(f"解析就业数据行时出错: {str(e)}")
                continue
            except Exception as e:
                logger.error(f"处理就业数据行时出错: {str(e)}")
                continue
    
    logger.info(f"成功加载 {len(EMPLOYMENT_DATA)} 所学校的就业数据")
    
    # 初始化默认值
    if EMPLOYMENT_DATA:
        try:
            init_default_values(EMPLOYMENT_DATA)
            logger.info("成功初始化就业数据默认值")
        except Exception as e:
            logger.error(f"初始化就业数据默认值时出错: {str(e)}")
            logger.exception(e)
except Exception as e:
    logger.error(f"加载就业数据失败: {str(e)}")
    logger.exception(e)

# 打印学校层级数据
try:
    for level, schools in city_level_map.items():
        logger.info(f"{level} 层级的学校数量: {len(schools)}")
except Exception as e:
    logger.error(f"打印学校层级数据时出错: {str(e)}")
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
    
    # 合并专业和方向为一个集合
    target_majors_and_directions = set(target_info.majors + target_info.directions)
    
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
        
        # 检查专业或研究方向是否匹配
        if target_majors_and_directions:
            # 获取学校的专业名称和所有研究方向名称
            school_major = school_data['major']
            school_directions = [d['yjfxmc'] for d in school_data.get('directions', [])]
            
            # 检查是否有任何一个匹配
            major_direction_match = (
                school_major in target_majors_and_directions or
                any(direction in target_majors_and_directions for direction in school_directions)
            )
            
            if not major_direction_match:
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

def _convert_school_info_to_dict(school_info: SchoolInfo) -> Dict:
    """将SchoolInfo对象转换为可JSON序列化的字典"""
    return {
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
        "city": school_info.city
    }

def analyze_schools(user_info: UserInfo, target_info: TargetInfo) -> Dict:
    """分析学校列表"""
    try:
        # 初始化评分计算器
        school_chooser = SchoolChooser(user_info, target_info)
        
        # 获取所有符合条件的学校
        schools = _filter_schools(target_info)
        logger.info(f"找到 {len(schools)} 所候选学校")
        
        # 计算每所学校的得分
        school_scores = []
        for school in schools:
            try:
                # 计算学校评分
                score_info = school_chooser._calculate_school_score(school)
                
                # 获取各评分卡得分
                location_score = school_chooser.location_calculator.calculate_total_score(school)
                major_score = school_chooser.major_calculator.calculate_total_score(school)
                advanced_study_score = school_chooser.advanced_calculator.calculate_total_score(
                    school, 
                    EMPLOYMENT_DATA.get(school.school_name, [])
                )
                
                # 转换为目标格式
                target_school = _convert_to_target_school(school, {
                    'score_info': {
                        'score_card': {
                            'location_card': location_score,
                            'major_card': major_score,
                            'advanced_study_card': advanced_study_score
                        },
                        'probability': score_info['probability'],
                        'total_score': score_info['total_score']
                    }
                })
                school_scores.append(target_school)
            except Exception as e:
                logger.error(f"计算学校 {school.school_name} 评分时出错: {str(e)}")
                continue
        
        # 按总分排序
        school_scores.sort(key=lambda x: float(x["total_score"]), reverse=True)
        
        # 添加排名
        for i, score in enumerate(school_scores):
            score["rank"] = i + 1
            
        # 按录取概率等级分组
        probability_groups = {
            '冲刺': [],  # 25-45%
            '稳妥': [],  # 45-75%
            '保底': []   # 75-95%
        }
        
        # 将学校分到不同概率组
        for score in school_scores:
            probability = float(score['admission_probability'].rstrip('%'))  # 移除百分号并转换为浮点数
            if PROBABILITY_LEVELS['IMPOSSIBLE'] <= probability < PROBABILITY_LEVELS['DIFFICULT']:
                probability_groups['冲刺'].append(score)
            elif PROBABILITY_LEVELS['DIFFICULT'] <= probability < PROBABILITY_LEVELS['MODERATE']:
                probability_groups['稳妥'].append(score)
            elif PROBABILITY_LEVELS['MODERATE'] <= probability < PROBABILITY_LEVELS['EASY']:
                probability_groups['保底'].append(score)
        
        # 在每个组内按总分排序并选择前三名
        recommended_schools = []
        for level, schools in probability_groups.items():
            schools.sort(key=lambda x: float(x['total_score']), reverse=True)
            top_schools = schools[:3]
            for school in top_schools:
                school['probability_level'] = level  # 添加概率等级标记
            recommended_schools.extend(top_schools)
        
        return {
            "code": 0,
            "data": {
                "probability_groups": probability_groups,
                "total": len(school_scores),
                "schools": recommended_schools  # 返回每个组内得分最高的前三所学校
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

class SchoolChooser:
    """学校选择器"""
    
    def __init__(self, user_info: UserInfo, target_info: TargetInfo):
        self.user_info = user_info
        self.target_info = target_info
        self.admission_calculator = AdmissionScoreCalculator(user_info, target_info)
        self.location_calculator = LocationScoreCalculator(user_info, target_info)
        self.major_calculator = MajorScoreCalculator(user_info, target_info)
        self.advanced_calculator = AdvancedStudyScoreCalculator(user_info, target_info)
        
    def _get_weight(self, name: str) -> float:
        """获取指定维度的权重"""
        for weight in self.target_info.weights:
            if weight.name == name:
                return weight.val
        return 0.33  # 默认权重
        
    def _calculate_school_score(self, school: SchoolInfo) -> Dict:
        """计算学校的综合得分"""
        # 计算三个维度的得分
        admission_score = self.admission_calculator.calculate(school)
        location_score = self.location_calculator.calculate_total_score(school)
        major_score = self.major_calculator.calculate_total_score(school)
        
        # 获取权重
        admission_weight = self._get_weight('考上概率')
        location_weight = self._get_weight('地理位置')
        major_weight = self._get_weight('专业实力')
        
        # 计算加权总分
        total_score = (
            admission_score['total_score'] * admission_weight +
            location_score['total_score'] * location_weight +
            major_score['total_score'] * major_weight
        )
        
        return {
            'school_name': school.school_name,
            'major': school.major,
            'total_score': round(total_score, 2),
            'probability': admission_score['probability'],  # 添加概率字段
            'level': admission_score['level'],
            'admission_score': admission_score,
            'location_score': location_score,
            'major_score': major_score
        }
        
    def _group_schools_by_probability(self, schools: List[SchoolInfo]) -> Dict[str, List[Dict]]:
        """将学校按照录取概率分组"""
        grouped_schools = {
            '冲刺': [],  # 25-45%
            '稳妥': [],  # 45-75%
            '保底': []   # 75-95%
        }
        
        for school in schools:
            school_score = self._calculate_school_score(school)
            probability = school_score['probability']
            
            if PROBABILITY_LEVELS['IMPOSSIBLE'] <= probability < PROBABILITY_LEVELS['DIFFICULT']:
                grouped_schools['冲刺'].append(school_score)
            elif PROBABILITY_LEVELS['DIFFICULT'] <= probability < PROBABILITY_LEVELS['MODERATE']:
                grouped_schools['稳妥'].append(school_score)
            elif PROBABILITY_LEVELS['MODERATE'] <= probability < PROBABILITY_LEVELS['EASY']:
                grouped_schools['保底'].append(school_score)
                
        # 在每个分组内按总分排序
        for level in grouped_schools:
            grouped_schools[level].sort(key=lambda x: x['total_score'], reverse=True)
            grouped_schools[level] = grouped_schools[level][:3]  # 只保留前三名
            
        return grouped_schools
        
    def choose_schools(self, schools: List[SchoolInfo]) -> Dict[str, List[Dict]]:
        """
        选择推荐学校
        :param schools: 候选学校列表
        :return: 按录取概率分组的推荐学校，每组返回得分最高的前三所
        """
        return self._group_schools_by_probability(schools)

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

def _calculate_school_score(score_card: Dict, admission_info: Dict) -> float:
    """计算学校总评分"""
    # 计算评分卡总分
    card_total_score = 0
    for card_name, weight in SCORE_CARD_WEIGHTS.items():
        card = score_card.get(card_name, {})
        score = card.get('total_score', 0)
        card_total_score += score * weight
    
    return card_total_score

def _convert_to_target_school(school_info: SchoolInfo, score_info: Dict) -> Dict:
    """将学校信息转换为目标格式"""
    score_card = score_info['score_info']['score_card']
    admission_info = score_info['score_info']
    
    # 获取学校层级
    levels = []
    if school_info.is_985 == "1":
        levels.append("985")
    if school_info.is_211 == "1":
        levels.append("211")
    if school_info.school_name in city_level_map.get('c9', set()):
        levels.append("C9")
        
    # 处理报录比数据
    blb_score = {}
    for blb in school_info.blb:
        try:
            year = blb.get('year')
            if year:
                blb_score[str(year)] = blb.get('blb', '0%')
        except:
            continue
            
    return {
        "school_name": school_info.school_name,
        "levels": levels,
        "city": school_info.city,
        "major_name": school_info.major,
        "major_code": school_info.major_code,
        "admission_probability": f"{admission_info['probability']}%",
        "total_score": str(_calculate_school_score(score_card, admission_info)),
        "location_score": score_card.get('location_card', {
            "dimension_scores": [],
            "total_score": 0,
            "school_name": school_info.school_name
        }),
        "major_score": score_card.get('major_card', {
            "dimension_scores": [],
            "total_score": 0,
            "school_name": school_info.school_name
        }),
        "sx_score": score_card.get('advanced_study_card', {
            "dimension_scores": [],
            "total_score": 0,
            "school_name": school_info.school_name
        }),
        "blb_score": blb_score,
        "fsx_score": score_info.get('fsx_score', {}),
        "nlqrs": score_info.get('nlqrs', 0)
    } 