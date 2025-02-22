import json
from typing import Dict, List, Any, Tuple
from loguru import logger
from statistics import median
import numpy as np
from scipy import stats
from collections import defaultdict
from wxcloudrun.beans.input_models import UserInfo, TargetInfo, SchoolInfo
from wxcloudrun.utils.file_util import CITY_LEVEL_MAP

# 全局变量存储数据
EMPLOYMENT_DATA = {}  # 就业数据

# 默认值配置
SYSTEM_EMPLOYMENT_WEIGHTS = {
    '公务员占比': 0.4,
    '事业单位占比': 0.3,
    '国有企业占比': 0.3
}

# 评分等级描述
SYSTEM_EMPLOYMENT_LEVELS = {
    'high': {
        'threshold': 80,
        'descriptions': {
            '公务员占比': '公务员就业机会优秀',
            '事业单位占比': '事业单位就业机会优秀',
            '国有企业占比': '国企就业机会优秀'
        }
    },
    'medium': {
        'threshold': 60,
        'descriptions': {
            '公务员占比': '公务员就业机会良好',
            '事业单位占比': '事业单位就业机会良好',
            '国有企业占比': '国企就业机会良好'
        }
    },
    'low': {
        'threshold': 0,
        'descriptions': {
            '公务员占比': '公务员就业机会一般',
            '事业单位占比': '事业单位就业机会一般',
            '国有企业占比': '国企就业机会一般'
        }
    }
}

# 默认值
DEFAULT_VALUES = {
    'C9': {'公务员占比': 20, '事业单位占比': 15, '国有企业占比': 30},
    '985': {'公务员占比': 15, '事业单位占比': 12, '国有企业占比': 25},
    '211': {'公务员占比': 10, '事业单位占比': 10, '国有企业占比': 20},
    '其他': {'公务员占比': 5, '事业单位占比': 8, '国有企业占比': 15}
}

def calculate_default_values():
    """计算各层级的默认值"""
    global DEFAULT_VALUES
    
    # 按层级收集数据
    level_data = {
        'C9': {'公务员占比': [], '事业单位占比': [], '国有企业占比': []},
        '985': {'公务员占比': [], '事业单位占比': [], '国有企业占比': []},
        '211': {'公务员占比': [], '事业单位占比': [], '国有企业占比': []},
        '其他': {'公务员占比': [], '事业单位占比': [], '国有企业占比': []}
    }
    
    # 遍历所有学校数据
    for school_name in EMPLOYMENT_DATA:
        level = get_school_level(school_name)
        
        # 计算各项占比
        for ratio_type in ['公务员占比', '事业单位占比', '国有企业占比']:
            ratio = calculate_average_ratio(school_name, ratio_type)
            if ratio is not None:
                level_data[level][ratio_type].append(ratio)
    
    # 计算每个层级的平均值
    for level in level_data:
        for ratio_type in level_data[level]:
            values = level_data[level][ratio_type]
            DEFAULT_VALUES[level][ratio_type] = np.mean(values) if values else 0

def load_data():
    """加载就业数据"""
    global EMPLOYMENT_DATA
    try:
        with open('wxcloudrun/resources/aggregated_employment_data.jsonl', 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                EMPLOYMENT_DATA[data['school_name']] = data['years_data']
        logger.info(f"成功加载 {len(EMPLOYMENT_DATA)} 所学校的就业数据")
        
        # 计算默认值
        calculate_default_values()
        logger.info(f"成功计算默认值: {DEFAULT_VALUES}")
    except Exception as e:
        logger.error(f"加载就业数据失败: {str(e)}")

def get_school_level(school_name: str) -> str:
    """获取学校层级"""
    if school_name in CITY_LEVEL_MAP.get('c9', set()):
        return 'C9'
    if school_name in CITY_LEVEL_MAP.get('985', set()):
        return '985'
    if school_name in CITY_LEVEL_MAP.get('211', set()):
        return '211'
    return '其他'

def calculate_average_ratio(school_name: str, ratio_type: str) -> float:
    """计算学校某个比例的平均值"""
    try:
        years_data = EMPLOYMENT_DATA.get(school_name, [])
        ratios = []
        for year_data in years_data:
            emp_data = year_data.get('employment_data', {}).get('就业情况', {})
            system_data = emp_data.get('体制内就业', {})
            if system_data and ratio_type in system_data:
                try:
                    ratio_str = str(system_data[ratio_type]).strip('%')  # 处理百分号
                    ratio = float(ratio_str)
                    ratios.append(ratio)
                except (ValueError, TypeError):
                    continue
        
        return np.mean(ratios) if ratios else None
    except Exception as e:
        logger.error(f"计算{school_name}的{ratio_type}平均值时出错: {str(e)}")
        return None

def calculate_percentile_score(value: float, all_values: List[float]) -> float:
    """计算分位数得分"""
    if not value or not all_values:
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

class SystemEmploymentScoreCalculator:
    """体制内就业评分计算器"""
    
    def __init__(self, user_info: UserInfo, target_info: TargetInfo):
        self.user_info = user_info
        self.target_info = target_info
        self.weights = SYSTEM_EMPLOYMENT_WEIGHTS
        
    def _get_description(self, dimension: str, score: float) -> str:
        """获取维度描述"""
        if score >= SYSTEM_EMPLOYMENT_LEVELS['high']['threshold']:
            return SYSTEM_EMPLOYMENT_LEVELS['high']['descriptions'][dimension]
        elif score >= SYSTEM_EMPLOYMENT_LEVELS['medium']['threshold']:
            return SYSTEM_EMPLOYMENT_LEVELS['medium']['descriptions'][dimension]
        return SYSTEM_EMPLOYMENT_LEVELS['low']['descriptions'][dimension]

    def calculate_ratio_score(self, school_info: SchoolInfo, ratio_type: str) -> Dict:
        """计算各类占比得分"""
        try:
            # 获取该学校的平均占比
            ratio = calculate_average_ratio(school_info.school_name, ratio_type)
            
            if ratio is None:
                # 使用对应层级的平均值作为默认值
                level = get_school_level(school_info.school_name)
                return {
                    'score': DEFAULT_VALUES[level][ratio_type],
                    'source': 'default',
                    'raw_value': DEFAULT_VALUES[level][ratio_type]  # 添加原始值
                }
            
            # 获取所有学校的该类占比
            all_ratios = []
            for school_name in EMPLOYMENT_DATA:
                r = calculate_average_ratio(school_name, ratio_type)
                if r is not None:
                    all_ratios.append(r)
            
            # 计算分位数得分
            score = calculate_percentile_score(ratio, all_ratios)
            return {
                'score': score,
                'source': 'real',
                'raw_value': ratio
            }
        except Exception as e:
            logger.error(f"计算{ratio_type}得分时出错: {str(e)}")
            level = get_school_level(school_info.school_name)
            return {
                'score': DEFAULT_VALUES[level][ratio_type],
                'source': 'default',
                'raw_value': DEFAULT_VALUES[level][ratio_type]  # 添加原始值
            }

    def calculate_total_score(self, school_info: SchoolInfo) -> Dict:
        """计算总分"""
        try:
            # 计算各维度得分
            civil_servant = self.calculate_ratio_score(school_info, '公务员占比')
            institution = self.calculate_ratio_score(school_info, '事业单位占比')
            state_owned = self.calculate_ratio_score(school_info, '国有企业占比')
            
            # 计算加权得分
            dimension_scores = [
                {
                    'name': '公务员占比',
                    'score': civil_servant['score'],
                    'weight': self.weights['公务员占比'],
                    'weighted_score': civil_servant['score'] * self.weights['公务员占比'],
                    'source': civil_servant['source'],
                    'raw_value': civil_servant.get('raw_value'),
                    'description': self._get_description('公务员占比', civil_servant['score'])
                },
                {
                    'name': '事业单位占比',
                    'score': institution['score'],
                    'weight': self.weights['事业单位占比'],
                    'weighted_score': institution['score'] * self.weights['事业单位占比'],
                    'source': institution['source'],
                    'raw_value': institution.get('raw_value'),
                    'description': self._get_description('事业单位占比', institution['score'])
                },
                {
                    'name': '国有企业占比',
                    'score': state_owned['score'],
                    'weight': self.weights['国有企业占比'],
                    'weighted_score': state_owned['score'] * self.weights['国有企业占比'],
                    'source': state_owned['source'],
                    'raw_value': state_owned.get('raw_value'),
                    'description': self._get_description('国有企业占比', state_owned['score'])
                }
            ]
            
            # 计算总分
            total_score = sum(score['weighted_score'] for score in dimension_scores)
            
            return {
                'dimension_scores': dimension_scores,
                'total_score': total_score,
                'school_name': school_info.school_name
            }
        except Exception as e:
            logger.error(f"计算总分时出错: {str(e)}")
            return {
                'dimension_scores': [],
                'total_score': 0,
                'school_name': school_info.school_name
            }

# 初始化数据
load_data() 