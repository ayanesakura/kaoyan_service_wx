import json
from typing import Dict, List, Any, Tuple
from loguru import logger
from statistics import median
import numpy as np
from scipy import stats
from collections import defaultdict
from wxcloudrun.beans.input_models import UserInfo, TargetInfo, SchoolInfo
from wxcloudrun.utils.file_util import CITY_LEVEL_MAP
from wxcloudrun.score_card.constants import (
    NON_SYSTEM_EMPLOYMENT_WEIGHTS,
    NON_SYSTEM_EMPLOYMENT_DEFAULTS,
    NON_SYSTEM_EMPLOYMENT_LEVELS
)

# 全局变量存储数据
EMPLOYMENT_DATA = {}  # 就业数据
SCHOOL_SATISFACTION_DATA = {}  # 学校满意度数据
MAJOR_SATISFACTION_DATA = defaultdict(dict)  # 专业满意度数据，格式: {major_name: {school_name: satisfaction}}

# 修改默认值定义
DEFAULT_VALUES = NON_SYSTEM_EMPLOYMENT_DEFAULTS

def load_data():
    """加载所有需要的数据"""
    global EMPLOYMENT_DATA, SCHOOL_SATISFACTION_DATA, MAJOR_SATISFACTION_DATA
    
    # 加载就业数据
    try:
        with open('wxcloudrun/resources/aggregated_employment_data.jsonl', 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                EMPLOYMENT_DATA[data['school_name']] = data['years_data']
    except Exception as e:
        logger.error(f"加载就业数据失败: {str(e)}")
        
    # 加载学校和专业满意度数据
    try:
        with open('wxcloudrun/resources/merged_school_data.jsonl', 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                school_name = data['school_name']
                major_name = data['major_name']
                
                # 学校满意度数据
                if data.get('school_environment_satisfaction'):
                    SCHOOL_SATISFACTION_DATA[school_name] = float(data['school_environment_satisfaction'])
                    
                # 专业满意度数据
                if data.get('major_satisfaction_employment'):
                    MAJOR_SATISFACTION_DATA[major_name][school_name] = float(data['major_satisfaction_employment'])
    except Exception as e:
        logger.error(f"加载满意度数据失败: {str(e)}")

    # 计算各层级的默认值
    calculate_default_values()

def calculate_default_values():
    """计算各层级的默认值"""
    global DEFAULT_VALUES
    
    # 按层级收集数据
    level_data = {
        'C9': {'就业率': [], '学校满意度': [], '专业满意度': []},
        '985': {'就业率': [], '学校满意度': [], '专业满意度': []},
        '211': {'就业率': [], '学校满意度': [], '专业满意度': []},
        '其他': {'就业率': [], '学校满意度': [], '专业满意度': []}
    }
    
    # 遍历所有学校数据
    for school_name in EMPLOYMENT_DATA:
        level = get_school_level(school_name)
        
        # 计算就业率
        emp_rate = calculate_average_employment_rate(school_name)
        if emp_rate is not None:
            level_data[level]['就业率'].append(emp_rate)
            
        # 学校满意度
        if school_name in SCHOOL_SATISFACTION_DATA:
            level_data[level]['学校满意度'].append(SCHOOL_SATISFACTION_DATA[school_name])
            
        # 专业满意度（取平均）
        major_sats = []
        for major_data in MAJOR_SATISFACTION_DATA.values():
            if school_name in major_data:
                major_sats.append(major_data[school_name])
        if major_sats:
            level_data[level]['专业满意度'].append(np.mean(major_sats))
    
    # 计算每个层级的中位数
    for level in level_data:
        for metric in level_data[level]:
            values = level_data[level][metric]
            DEFAULT_VALUES[level][metric] = median(values) if values else 0

def get_school_level(school_name: str) -> str:
    """获取学校层级"""
    if school_name in CITY_LEVEL_MAP.get('c9', set()):
        return 'C9'
    if school_name in CITY_LEVEL_MAP.get('985', set()):
        return '985'
    if school_name in CITY_LEVEL_MAP.get('211', set()):
        return '211'
    return '其他'

def calculate_average_employment_rate(school_name: str) -> float:
    """计算学校的平均就业率"""
    try:
        years_data = EMPLOYMENT_DATA.get(school_name, [])
        rates = []
        for year_data in years_data:
            emp_data = year_data.get('employment_data', {}).get('就业情况', {})
            if emp_data and '就业率' in emp_data:
                try:
                    rate = float(emp_data['就业率'])
                    rates.append(rate)
                except (ValueError, TypeError):
                    continue
        return np.mean(rates) if rates else None
    except Exception as e:
        logger.error(f"计算平均就业率时出错: {str(e)}")
        return None

def calculate_percentile_score(value: float, all_values: List[float]) -> float:
    """计算分位数得分"""
    if not all_values or value is None:
        return 0
    try:
        all_values = np.array(all_values)
        all_values = all_values[~np.isnan(all_values)]  # 移除NaN值
        if len(all_values) == 0:
            return 0
        percentile = stats.percentileofscore(all_values, value)
        return max(1, min(99, percentile))  # 限制在1-99之间
    except Exception as e:
        logger.error(f"计算分位数得分时出错: {str(e)}")
        return 0

class NonSystemEmploymentScoreCalculator:
    """非体制就业评分计算器"""
    
    def __init__(self, user_info: UserInfo, target_info: TargetInfo):
        self.user_info = user_info
        self.target_info = target_info
        self.weights = NON_SYSTEM_EMPLOYMENT_WEIGHTS
        
    def _get_description(self, dimension: str, score: float) -> str:
        """获取维度描述"""
        if score >= NON_SYSTEM_EMPLOYMENT_LEVELS['high']['threshold']:
            return NON_SYSTEM_EMPLOYMENT_LEVELS['high']['descriptions'][dimension]
        elif score >= NON_SYSTEM_EMPLOYMENT_LEVELS['medium']['threshold']:
            return NON_SYSTEM_EMPLOYMENT_LEVELS['medium']['descriptions'][dimension]
        return NON_SYSTEM_EMPLOYMENT_LEVELS['low']['descriptions'][dimension]

    def calculate_employment_rate_score(self, school_info: SchoolInfo) -> Dict:
        """计算就业率得分"""
        try:
            # 获取该学校的平均就业率
            emp_rate = calculate_average_employment_rate(school_info.school_name)
            if emp_rate is None:
                # 使用默认值
                level = get_school_level(school_info.school_name)
                return {
                    'score': DEFAULT_VALUES[level]['就业率'],
                    'source': 'default'
                }
            
            # 获取所有学校的就业率
            all_rates = []
            for school_name in EMPLOYMENT_DATA:
                rate = calculate_average_employment_rate(school_name)
                if rate is not None:
                    all_rates.append(rate)
            
            # 计算分位数得分
            score = calculate_percentile_score(emp_rate, all_rates)
            return {
                'score': score,
                'source': 'real',
                'raw_value': emp_rate
            }
        except Exception as e:
            logger.error(f"计算就业率得分时出错: {str(e)}")
            level = get_school_level(school_info.school_name)
            return {
                'score': DEFAULT_VALUES[level]['就业率'],
                'source': 'default'
            }

    def calculate_school_satisfaction_score(self, school_info: SchoolInfo) -> Dict:
        """计算学校就业满意度得分"""
        try:
            satisfaction = SCHOOL_SATISFACTION_DATA.get(school_info.school_name)
            if satisfaction is None:
                level = get_school_level(school_info.school_name)
                return {
                    'score': DEFAULT_VALUES[level]['学校满意度'],
                    'source': 'default'
                }
            
            # 计算分位数得分
            score = calculate_percentile_score(
                satisfaction,
                list(SCHOOL_SATISFACTION_DATA.values())
            )
            return {
                'score': score,
                'source': 'real',
                'raw_value': satisfaction
            }
        except Exception as e:
            logger.error(f"计算学校满意度得分时出错: {str(e)}")
            level = get_school_level(school_info.school_name)
            return {
                'score': DEFAULT_VALUES[level]['学校满意度'],
                'source': 'default'
            }

    def calculate_major_satisfaction_score(self, school_info: SchoolInfo) -> Dict:
        """计算专业就业满意度得分"""
        try:
            major_data = MAJOR_SATISFACTION_DATA.get(school_info.major, {})
            satisfaction = major_data.get(school_info.school_name)
            
            if satisfaction is None:
                level = get_school_level(school_info.school_name)
                return {
                    'score': DEFAULT_VALUES[level]['专业满意度'],
                    'source': 'default'
                }
            
            # 计算分位数得分
            score = calculate_percentile_score(
                satisfaction,
                list(major_data.values())
            )
            return {
                'score': score,
                'source': 'real',
                'raw_value': satisfaction
            }
        except Exception as e:
            logger.error(f"计算专业满意度得分时出错: {str(e)}")
            level = get_school_level(school_info.school_name)
            return {
                'score': DEFAULT_VALUES[level]['专业满意度'],
                'source': 'default'
            }

    def calculate_total_score(self, school_info: SchoolInfo) -> Dict:
        """计算总分"""
        # 计算各维度得分
        emp_rate = self.calculate_employment_rate_score(school_info)
        school_sat = self.calculate_school_satisfaction_score(school_info)
        major_sat = self.calculate_major_satisfaction_score(school_info)
        
        # 计算加权得分
        dimension_scores = [
            {
                'name': '就业率',
                'score': emp_rate['score'],
                'weight': self.weights['就业率'],
                'weighted_score': emp_rate['score'] * self.weights['就业率'],
                'source': emp_rate['source'],
                'raw_value': emp_rate.get('raw_value'),
                'description': self._get_description('就业率', emp_rate['score'])
            },
            {
                'name': '学校满意度',
                'score': school_sat['score'],
                'weight': self.weights['学校满意度'],
                'weighted_score': school_sat['score'] * self.weights['学校满意度'],
                'source': school_sat['source'],
                'raw_value': school_sat.get('raw_value'),
                'description': self._get_description('学校满意度', school_sat['score'])
            },
            {
                'name': '专业满意度',
                'score': major_sat['score'],
                'weight': self.weights['专业满意度'],
                'weighted_score': major_sat['score'] * self.weights['专业满意度'],
                'source': major_sat['source'],
                'raw_value': major_sat.get('raw_value'),
                'description': self._get_description('专业满意度', major_sat['score'])
            }
        ]
        
        # 计算总分
        total_score = sum(score['weighted_score'] for score in dimension_scores)
        
        return {
            'dimension_scores': dimension_scores,
            'total_score': total_score,
            'school_name': school_info.school_name
        }

# 初始化数据
load_data() 