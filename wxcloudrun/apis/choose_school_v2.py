import json
from typing import List, Dict, Any, Tuple
from loguru import logger
from flask import request, jsonify, current_app
from wxcloudrun.beans.input_models import UserInfo, TargetInfo, SchoolInfo, Area
from wxcloudrun.score_card.admission_score_calculator import AdmissionScoreCalculator
from wxcloudrun.score_card.location_score_calculator import LocationScoreCalculator
from wxcloudrun.score_card.major_score_calculator import MajorScoreCalculator
from wxcloudrun.score_card.system_employment_score_calculator import SystemEmploymentScoreCalculator
from wxcloudrun.score_card.non_system_employment_score_calculator import NonSystemEmploymentScoreCalculator
from wxcloudrun.score_card.constants import PROBABILITY_LEVELS, SCORE_CARD_WEIGHTS, TOTAL_SCORE_WEIGHTS, ADMISSION_SCORE_WEIGHTS, ADMISSION_SCORE_DEFAULTS, ADMISSION_SCORE_LEVELS
from wxcloudrun.utils.file_util import SCHOOL_DATAS, EMPLOYMENT_DATA, CITY_LEVEL_MAP
from wxcloudrun.score_card.advanced_study_score_calculator import AdvancedStudyScoreCalculator
import os
import pickle
from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from wxcloudrun.score_card.score_data_loader import (
    get_school_data,
    get_major_data,
    SCHOOL_DATA,
    MAJOR_DATA
)

# 定义本地缓存文件路径
city_level_map = CITY_LEVEL_MAP


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
        # 获取学校数据，检查软科排名
        school_name = school_data['school_name']
        school_info_data = get_school_data(school_name)
        
        # 如果学校没有软科排名数据，跳过这个学校
        if not school_info_data or school_info_data.rank is None:
            logger.warning(f"学校 {school_name} 没有软科排名数据，将被过滤掉")
            continue
            
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
    # 获取就业数据
    employment_info = EMPLOYMENT_DATA.get(school_info.school_name, [])
    
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
        "city": school_info.city,
        "jy": employment_info  # 添加就业数据
    }

def analyze_schools(user_info: UserInfo, target_info: TargetInfo, debug: bool = False) -> Dict:
    """分析学校列表"""
    try:
        # 获取所有符合条件的学校
        schools = _filter_schools(target_info)
        target_schools = [(school.school_name, school.major_code) for school in schools]
        # 初始化评分计算器
        school_chooser = SchoolChooser(user_info, target_info, target_schools)
        

        logger.info(f"找到 {len(schools)} 所候选学校")
        
        # 计算每所学校的得分
        school_scores = []
        for school in schools:
            try:
                # 计算学校评分
                score_info = school_chooser._calculate_school_score(school)
                
                # 获取各评分卡得分
                location_score = score_info['location_score']
                major_score = score_info['major_score']
                advanced_study_score = score_info['advanced_study_score']
                admission_score = score_info['admission_score']
                system_employment_score = score_info['system_employment_score']
                non_system_employment_score = score_info['non_system_employment_score']
                
                # 转换为目标格式
                target_school = _convert_to_target_school(school, {
                    'score_info': {
                        'score_card': {
                            'location_card': location_score,
                            'major_card': major_score,
                            'advanced_study_card': advanced_study_score,
                            'admission_score': admission_score,
                            'system_employment_card': system_employment_score,
                            'non_system_employment_card': non_system_employment_score
                        },
                        'probability': score_info['probability'],
                        'total_score': score_info['total_score']
                    }
                })
                
                # 在debug模式下添加学校详情
                if debug:
                    target_school['school_detail'] = _convert_school_info_to_dict(school)
                    target_school['score_info'] = score_info
                
                school_scores.append(target_school)
            except Exception as e:
                # 在182行添加更详细的错误日志
                logger.error(
                    f"计算学校 {school.school_name} 评分时出错:\n"
                    f"错误类型: {type(e).__name__}\n"
                    f"错误信息: {str(e)}\n"
                    f"错误位置: {e.__traceback__.tb_frame.f_code.co_filename}:{e.__traceback__.tb_lineno}\n"
                    f"学校信息: {vars(school)}\n"
                    f"目标信息: {vars(target_info)}\n"
                    f"用户信息: {vars(user_info)}\n"
                    f"当前评分卡状态:\n"
                    f"- location_calculator: {vars(school_chooser.location_calculator)}\n"
                    f"- major_calculator: {vars(school_chooser.major_calculator)}\n"
                    f"- admission_calculator: {vars(school_chooser.admission_calculator)}\n"
                    f"- system_employment_calculator: {vars(school_chooser.system_employment_calculator)}\n"
                    f"- non_system_employment_calculator: {vars(school_chooser.non_system_employment_calculator)}\n"
                    f"- advanced_calculator: {vars(school_chooser.advanced_calculator)}"
                )
                logger.exception("完整错误栈:")
                continue
        
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
        for level in probability_groups:
            probability_groups[level].sort(key=lambda x: float(x['total_score']), reverse=True)
            probability_groups[level] = probability_groups[level][:3]  # 只保留前三名
        logger.info(f"最终学校列表: {probability_groups}")
        return {
            "code": 0,
            "data": probability_groups,
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
    
    def __init__(self, user_info: UserInfo, target_info: TargetInfo, target_schools: List[Tuple[str, str]]):
        self.user_info = user_info
        self.target_info = target_info
        self.target_schools = target_schools
        
        # 初始化所有评分计算器      
        self.location_calculator = LocationScoreCalculator(user_info, target_info)
        self.major_calculator = MajorScoreCalculator(user_info, target_info, target_schools)
        self.advanced_calculator = AdvancedStudyScoreCalculator(user_info, target_info, target_schools)
        self.admission_calculator = AdmissionScoreCalculator(user_info, target_info)
        # 添加新的评分计算器
        self.system_employment_calculator = SystemEmploymentScoreCalculator(user_info, target_info, target_schools)
        self.non_system_employment_calculator = NonSystemEmploymentScoreCalculator(user_info, target_info, target_schools)
        
        # 初始化权重
        self.weights = self._init_weights()
        
    def _init_weights(self) -> Dict[str, float]:
        """初始化权重"""
        weights = {
            '地理位置': 0.15,
            '专业实力': 0.15,
            '升学': 0.2,
            '录取概率': 0.2,
            '体制内就业': 0.15,  # 添加体制内就业权重
            '非体制就业': 0.15   # 添加非体制就业权重
        }
        
        # 如果有用户自定义权重，则使用用户定义的
        if self.target_info.weights:
            for weight in self.target_info.weights:
                if weight.name in weights:
                    weights[weight.name] = weight.val
                    
        return weights
        
    def _calculate_school_score(self, school: SchoolInfo) -> Dict:
        """计算学校的综合得分"""
        # 计算三个维度的得分
        admission_score = self.admission_calculator.calculate(school)
        location_score = self.location_calculator.calculate_total_score(school)
        major_score = self.major_calculator.calculate_total_score(school)
        system_employment_score = self.system_employment_calculator.calculate_total_score(school)
        non_system_employment_score = self.non_system_employment_calculator.calculate_total_score(school)
        advanced_study_score = self.advanced_calculator.calculate_total_score(school)
        
        # 获取权重
        location_weight = self.weights['地理位置']
        major_weight = self.weights['专业实力']
        advanced_study_weight = self.weights['升学']
        system_employment_weight = self.weights['体制内就业']
        non_system_employment_weight = self.weights['非体制就业']
        
        # 计算加权总分
        total_score = (
            location_score['total_score'] * location_weight +
            major_score['total_score'] * major_weight +
            advanced_study_score['total_score'] * advanced_study_weight +
            system_employment_score['total_score'] * system_employment_weight +
            non_system_employment_score['total_score'] * non_system_employment_weight
        )
        
        return {
            'school_name': school.school_name,
            'major': school.major,
            'total_score': round(total_score, 2),
            'probability': admission_score['probability'],  # 添加概率字段
            'level': admission_score['level'],
            'admission_score': admission_score,
            'location_score': location_score,
            'major_score': major_score,
            'advanced_study_score': advanced_study_score,
            'system_employment_score': system_employment_score,
            'non_system_employment_score': non_system_employment_score
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
            probability = school_score['admission_probability']
            
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
        request_data = request.get_json()


        user_info = UserInfo(**request_data['user_info'])
        target_info = TargetInfo(**request_data['target_info'])
        debug_mode = request_data.get('debug', False)
        
        result = analyze_schools(user_info, target_info, debug_mode)
        logger.info(f"choose_schools_v2 result: {result}")
        temp = json.dumps(request_data, ensure_ascii=False)
        logger.info(f"choose_schools_v2 request_data    : {temp}")
        return jsonify(result)
        
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
            
    # 处理分数线数据
    fsx_score = []
    for fsx in school_info.fsx:
        try:
            year_data = {
                'year': fsx.get('year'),
                '总分': 0,
                '科目1': 0,
                '科目2': 0,
                '科目3': 0,
                '科目4': 0
            }
            for subject in fsx.get('data', []):
                if subject.get('subject') == '总分':
                    year_data['总分'] = subject.get('score', 0)
                elif '科一' in subject.get('subject', ''):
                    year_data['科目1'] = subject.get('score', 0)
                elif '科二' in subject.get('subject', ''):
                    year_data['科目2'] = subject.get('score', 0)
                elif '科三' in subject.get('subject', ''):
                    year_data['科目3'] = subject.get('score', 0)
                elif '科四' in subject.get('subject', ''):
                    year_data['科目4'] = subject.get('score', 0)
            
            # 检查是否包含null或NaN
            has_invalid_score = False
            for score in year_data.values():
                if score is None or (isinstance(score, float) and str(score).lower() == 'nan'):
                    has_invalid_score = True
                    break
            
            # 只有当所有分数都有效时才添加数据
            if not has_invalid_score:
                fsx_score.append(year_data)
        except Exception as e:
            logger.error(f"处理分数线数据时出错: {str(e)}")
            continue
            
    # 计算nlqrs - 简化后的逻辑
    nlqrs = 0
    for direction in school_info.directions:
        try:
            zsrs = direction.get('zsrs', '')
            # 提取数字字符
            num_str = ''.join(c for c in zsrs if c.isdigit())
            if num_str:
                nlqrs += int(num_str)
        except Exception as e:
            logger.error(f"处理招生人数时出错: {str(e)}, zsrs={direction.get('zsrs')}")
            continue
    
    # 转换评分卡格式
    def convert_score_card(card_data: Dict) -> Dict:
        if not card_data:
            return {'total_score': 0}
        result = {}
        # 处理total_score
        total_score = card_data.get('total_score', 0)
        if isinstance(total_score, float):
            result['total_score'] = round(total_score, 1)
        else:
            result['total_score'] = total_score
            
        # 处理其他维度分数
        for dim in card_data.get('dimension_scores', []):
            score = dim['score']
            if isinstance(score, float):
                result[dim['name']] = round(score, 1)
            else:
                result[dim['name']] = score
        return result
    
    return {
        "school_name": school_info.school_name,
        "levels": levels,
        "city": school_info.city,
        "major_name": school_info.major,
        "major_code": school_info.major_code,
        "admission_probability": f"{admission_info['probability']}%",
        "admission_score": convert_score_card(score_card.get('admission_score')),
        "total_score": str(round(float(_calculate_school_score(score_card, admission_info)), 1)),
        "location_score": convert_score_card(score_card.get('location_card')),
        "major_score": convert_score_card(score_card.get('major_card')),
        "sx_score": convert_score_card(score_card.get('advanced_study_card')),
        "tzjy_score": convert_score_card(score_card.get('system_employment_card')),
        "ftzjy_score": convert_score_card(score_card.get('non_system_employment_card')),
        "blb_score": blb_score,
        "fsx_score": fsx_score,
        "nlqrs": nlqrs
    }

router = APIRouter()

class ChooseSchoolRequest(BaseModel):
    user_info: Dict[str, Any]
    target_info: Dict[str, Any]

@router.post("/choose_school_v2")
async def choose_school_v2(request: ChooseSchoolRequest = Body(...)):
    """选校API V2版本
    
    Args:
        request: 请求体
        
    Returns:
        选校结果
    """
    try:
        # 解析请求参数
        user_info = UserInfo(**request.user_info)
        target_info = TargetInfo(**request.target_info)
        
        # 生成评分卡
        score_cards = generate_score_cards(user_info, target_info)
        
        # 计算总评分
        total_scores = calculate_total_scores(score_cards, target_info)
        
        # 返回结果
        return {
            "code": 0,
            "message": "success",
            "data": {
                "score_cards": score_cards,
                "total_scores": total_scores
            }
        }
    except Exception as e:
        logger.exception(f"选校API出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def generate_score_cards(user_info: UserInfo, target_info: TargetInfo) -> Dict[str, Any]:
    """生成评分卡
    
    Args:
        user_info: 用户信息
        target_info: 目标信息
        
    Returns:
        评分卡结果
    """
    # 准备目标学校和专业列表
    target_schools = [(school_info.school_name, school_info.major_code) for school_info in target_info.schools]
    
    # 初始化各评分计算器
    major_calculator = MajorScoreCalculator(user_info, target_info, target_schools)
    location_calculator = LocationScoreCalculator(user_info, target_info)
    
    # 计算专业评分
    major_scores = major_calculator.calculate_all_scores()
    
    # 计算地理位置评分
    location_scores = []
    for school_info in target_info.schools:
        try:
            location_score = location_calculator.calculate_score(school_info)
            location_scores.append(location_score)
        except Exception as e:
            logger.error(f"计算 {school_info.school_name} 的地理位置评分时出错: {str(e)}")
    
    # 根据用户意向计算就业或升学评分
    if target_info.intention == "就业":
        if target_info.employment_type == "体制内":
            employment_calculator = SystemEmploymentScoreCalculator(user_info, target_info, target_schools)
        else:
            employment_calculator = NonSystemEmploymentScoreCalculator(user_info, target_info, target_schools)
        
        employment_scores = employment_calculator.calculate_all_scores()
        advanced_study_scores = []
    else:  # 升学
        advanced_study_calculator = AdvancedStudyScoreCalculator(user_info, target_info, target_schools)
        advanced_study_scores = advanced_study_calculator.calculate_all_scores()
        employment_scores = []
    
    # 整合所有评分卡结果
    score_cards = {
        "major_card": major_scores,
        "location_card": location_scores
    }
    
    if target_info.intention == "就业":
        score_cards["employment_card"] = employment_scores
    else:
        score_cards["advanced_study_card"] = advanced_study_scores
    
    return score_cards

def calculate_admission_score(school_info: SchoolInfo, target_info: TargetInfo) -> Dict[str, Any]:
    """计算录取概率评分
    
    Args:
        school_info: 学校信息
        target_info: 目标信息
        
    Returns:
        录取概率评分
    """
    # 这里是录取概率评分的计算逻辑
    # 为简化示例，这里使用默认值
    dimension_scores = [
        {
            "name": "备考时间",
            "score": ADMISSION_SCORE_DEFAULTS["备考时间"],
            "weight": ADMISSION_SCORE_WEIGHTS["备考时间"],
            "weighted_score": ADMISSION_SCORE_DEFAULTS["备考时间"] * ADMISSION_SCORE_WEIGHTS["备考时间"],
            "description": ADMISSION_SCORE_LEVELS["low"]["descriptions"]["备考时间"]
        },
        # ... 其他维度的评分 ...
    ]
    
    total_score = sum(item["weighted_score"] for item in dimension_scores)
    
    return {
        "dimension_scores": dimension_scores,
        "total_score": total_score
    }

def calculate_total_scores(score_cards: Dict[str, List[Dict[str, Any]]], target_info: TargetInfo) -> List[Dict[str, Any]]:
    """计算总评分
    
    Args:
        score_cards: 评分卡结果
        target_info: 目标信息
        
    Returns:
        总评分结果
    """
    # 获取各评分卡
    major_scores = {f"{score['school_name']}_{score['major_code']}": score for score in score_cards.get("major_card", [])}
    location_scores = {f"{score['school_name']}_{score['major_code']}": score for score in score_cards.get("location_card", [])}
    
    if target_info.intention == "就业":
        employment_scores = {f"{score['school_name']}_{score['major_code']}": score for score in score_cards.get("employment_card", [])}
        advanced_study_scores = {}
    else:
        advanced_study_scores = {f"{score['school_name']}_{score['major_code']}": score for score in score_cards.get("advanced_study_card", [])}
        employment_scores = {}
    
    # 计算总评分
    total_scores = []
    
    for school_info in target_info.schools:
        key = f"{school_info.school_name}_{school_info.major_code}"
        
        # 获取各评分卡得分
        major_score = major_scores.get(key, {"total_score": 0})
        location_score = location_scores.get(key, {"total_score": 0})
        
        if target_info.intention == "就业":
            employment_score = employment_scores.get(key, {"total_score": 0})
            card_score = (
                major_score["total_score"] * SCORE_CARD_WEIGHTS["major_card"] +
                location_score["total_score"] * SCORE_CARD_WEIGHTS["location_card"] +
                employment_score["total_score"] * SCORE_CARD_WEIGHTS["employment_card"]
            )
        else:
            advanced_study_score = advanced_study_scores.get(key, {"total_score": 0})
            card_score = (
                major_score["total_score"] * SCORE_CARD_WEIGHTS["major_card"] +
                location_score["total_score"] * SCORE_CARD_WEIGHTS["location_card"] +
                advanced_study_score["total_score"] * SCORE_CARD_WEIGHTS["advanced_study_card"]
            )
        
        # 计算录取概率得分
        admission_score = calculate_admission_score(school_info, target_info)
        
        # 计算总分
        total_score = (
            card_score * TOTAL_SCORE_WEIGHTS["score_card"] +
            admission_score["total_score"] * TOTAL_SCORE_WEIGHTS["admission_probability"]
        )
        
        # 构建结果
        result = {
            "school_name": school_info.school_name,
            "major_code": school_info.major_code,
            "major_name": school_info.major_name,
            "total_score": total_score,
            "card_score": card_score,
            "admission_score": admission_score["total_score"],
            "major_score": major_score["total_score"],
            "location_score": location_score["total_score"]
        }
        
        if target_info.intention == "就业":
            result["employment_score"] = employment_score["total_score"]
        else:
            result["advanced_study_score"] = advanced_study_score["total_score"]
        
        total_scores.append(result)
    
    # 按总分排序
    total_scores.sort(key=lambda x: x["total_score"], reverse=True)
    
    return total_scores 