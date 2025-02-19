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
import os
import pickle

# 定义本地缓存文件路径
CACHE_DIR = 'wxcloudrun/cache'
SCHOOL_DATA_CACHE = os.path.join(CACHE_DIR, 'school_data.pkl')
EMPLOYMENT_DATA_CACHE = os.path.join(CACHE_DIR, 'employment_data.pkl')

def load_cached_data():
    """从本地缓存加载数据"""
    global SCHOOL_DATAS, EMPLOYMENT_DATA
    try:
        # 确保缓存目录存在
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)
            
        # 尝试加载学校数据
        if os.path.exists(SCHOOL_DATA_CACHE):
            with open(SCHOOL_DATA_CACHE, 'rb') as f:
                SCHOOL_DATAS = pickle.load(f)
                logger.info(f"从本地缓存加载 {len(SCHOOL_DATAS)} 条学校数据")
        
        # 尝试加载就业数据
        if os.path.exists(EMPLOYMENT_DATA_CACHE):
            with open(EMPLOYMENT_DATA_CACHE, 'rb') as f:
                EMPLOYMENT_DATA = pickle.load(f)
                logger.info(f"从本地缓存加载 {len(EMPLOYMENT_DATA)} 所学校的就业数据")
                
        return bool(SCHOOL_DATAS and EMPLOYMENT_DATA)
    except Exception as e:
        logger.error(f"从本地缓存加载数据时出错: {str(e)}")
        return False

def save_data_to_cache():
    """保存数据到本地缓存"""
    try:
        # 确保缓存目录存在
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)
            
        # 保存学校数据
        with open(SCHOOL_DATA_CACHE, 'wb') as f:
            pickle.dump(SCHOOL_DATAS, f)
            
        # 保存就业数据
        with open(EMPLOYMENT_DATA_CACHE, 'wb') as f:
            pickle.dump(EMPLOYMENT_DATA, f)
            
        logger.info("成功保存数据到本地缓存")
        return True
    except Exception as e:
        logger.error(f"保存数据到本地缓存时出错: {str(e)}")
        return False

# 初始化全局变量
SCHOOL_DATAS = None
EMPLOYMENT_DATA = {}

def ensure_data_loaded():
    """确保数据已加载"""
    global SCHOOL_DATAS, EMPLOYMENT_DATA
    
    if SCHOOL_DATAS is None:
        logger.info("学校数据未加载，开始加载数据...")
        try:
            # 从应用配置获取数据
            SCHOOL_DATAS = current_app.config.get('SCHOOL_DATAS', [])
            if SCHOOL_DATAS:
                logger.info(f"从应用配置加载 {len(SCHOOL_DATAS)} 条学校数据")
                # 更新city_level_map
                for data in SCHOOL_DATAS:
                    school_name = data.get('school_name')
                    is_985 = data.get('is_985')
                    is_211 = data.get('is_211')
                    if school_name:
                        if is_985 == "1":
                            city_level_map['985'].add(school_name)
                        if is_211 == "1":
                            city_level_map['211'].add(school_name)
            else:
                logger.error("应用配置中没有学校数据")
                SCHOOL_DATAS = []
                return False
        except Exception as e:
            logger.error(f"加载学校数据时出错: {str(e)}")
            logger.exception(e)
            SCHOOL_DATAS = []
            return False
    
    # 如果就业数据为空，加载就业数据
    if not EMPLOYMENT_DATA:
        employment_file = 'wxcloudrun/resources/aggregated_employment_data.jsonl'
        
        try:
            # 首先尝试加载主文件
            if os.path.exists(employment_file):
                with open(employment_file, 'r', encoding='utf-8') as f:
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
            
            if EMPLOYMENT_DATA:
                logger.info(f"成功加载 {len(EMPLOYMENT_DATA)} 所学校的就业数据")
                
                # 初始化默认值
                try:
                    init_default_values(EMPLOYMENT_DATA)
                    logger.info("成功初始化就业数据默认值")
                except Exception as e:
                    logger.error(f"初始化就业数据默认值时出错: {str(e)}")
                    logger.exception(e)
            else:
                logger.error("无法加载就业数据")
                return False
                
        except Exception as e:
            logger.error(f"加载就业数据失败: {str(e)}")
            logger.exception(e)
            return False
    
    # 打印学校层级数据
    try:
        for level, schools in city_level_map.items():
            logger.info(f"{level} 层级的学校数量: {len(schools)}")
    except Exception as e:
        logger.error(f"打印学校层级数据时出错: {str(e)}")
        logger.exception(e)
    
    return bool(SCHOOL_DATAS and EMPLOYMENT_DATA)

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
                location_score = score_info['location_score']
                major_score = score_info['major_score']
                advanced_study_score = score_info['advanced_study_score']
                admission_score = score_info['admission_score']
                
                # 转换为目标格式
                target_school = _convert_to_target_school(school, {
                    'score_info': {
                        'score_card': {
                            'location_card': location_score,
                            'major_card': major_score,
                            'advanced_study_card': advanced_study_score,
                            'admission_score': admission_score
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
                logger.error(f"计算学校 {school.school_name} 评分时出错: {str(e)}")
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
        advanced_study_score = self.advanced_calculator.calculate_total_score(
            school, 
            EMPLOYMENT_DATA.get(school.school_name, [])
        )   
        
        # 获取权重
        location_weight = self._get_weight('地理位置')
        major_weight = self._get_weight('专业实力')
        advanced_study_weight = self._get_weight('升学')
        
        # 计算加权总分
        total_score = (
            location_score['total_score'] * location_weight +
            major_score['total_score'] * major_weight +
            advanced_study_score['total_score'] * advanced_study_weight
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
            'advanced_study_score': advanced_study_score
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
        # 确保数据已加载
        if not ensure_data_loaded():
            return jsonify({
                "code": -1,
                "data": None,
                "message": "数据加载失败，请稍后重试"
            })
        
        # 获取请求参数
        request_data = request.get_json()
        
        if not SCHOOL_DATAS:
            return jsonify({
                "code": -1,
                "data": None,
                "message": "学校数据未正确加载"
            })

        user_info = UserInfo(**request_data['user_info'])
        target_info = TargetInfo(**request_data['target_info'])
        debug_mode = request_data.get('debug', False)
        
        result = analyze_schools(user_info, target_info, debug_mode)
        
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
        result = {'total_score': card_data.get('total_score', 0)}
        for dim in card_data.get('dimension_scores', []):
            result[dim['name']] = dim['score']
        return result
    
    return {
        "school_name": school_info.school_name,
        "levels": levels,
        "city": school_info.city,
        "major_name": school_info.major,
        "major_code": school_info.major_code,
        "admission_probability": f"{admission_info['probability']}%",
        "admission_score": convert_score_card(score_card.get('admission_score')),
        "total_score": str(_calculate_school_score(score_card, admission_info)),
        "location_score": convert_score_card(score_card.get('location_card')),
        "major_score": convert_score_card(score_card.get('major_card')),
        "sx_score": convert_score_card(score_card.get('advanced_study_card')),
        "tzjy_score": {},  # 待实现
        "ftzjy_score": {}, # 待实现
        "blb_score": blb_score,
        "fsx_score": fsx_score,
        "nlqrs": nlqrs
    } 