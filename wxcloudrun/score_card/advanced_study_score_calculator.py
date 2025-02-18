from typing import Dict, List, Any, Tuple
from loguru import logger
from wxcloudrun.score_card.constants import SCHOOL_LEVELS, ADVANCED_STUDY_WEIGHTS, SCORE_LEVELS
from wxcloudrun.apis.choose_schools import city_level_map, load_school_data
from wxcloudrun.beans.input_models import UserInfo, TargetInfo, SchoolInfo
import numpy as np
from statistics import median
from collections import defaultdict

# 确保学校数据已加载
if not city_level_map.get('211'):
    logger.info("学校层级数据未加载，开始加载数据...")
    load_school_data()
    if not city_level_map.get('211'):
        logger.error("学校层级数据加载失败")
# 打印不同层级学校的个数
for level, schools in city_level_map.items():
    logger.info(f"{level} 层级的学校数量: {len(schools)}")

# print(city_level_map)

# 全局变量存储默认值和最大值
DEFAULT_VALUES = {}
GLOBAL_MAX_VALUES = {
    '升学率': 0.0,
    '升学人数': 0,
    '升学率增长': 0.0,
    '留学质量': 0.0
}

# 全局变量存储就业数据
EMPLOYMENT_DATA = {}

def init_default_values(employment_data: Dict[str, List[Dict]]):
    """初始化各层级学校的默认值和全局最大值"""
    global DEFAULT_VALUES, GLOBAL_MAX_VALUES, EMPLOYMENT_DATA
    EMPLOYMENT_DATA = employment_data  # 保存就业数据
    DEFAULT_VALUES, GLOBAL_MAX_VALUES = _calculate_values(employment_data)
    logger.info(f"计算得到的默认值: {DEFAULT_VALUES}")
    logger.info(f"计算得到的全局最大值: {GLOBAL_MAX_VALUES}")

def _calculate_values(employment_data: Dict[str, List[Dict]]) -> Tuple[Dict[str, Dict[str, float]], Dict[str, float]]:
    """计算各层级学校的默认值和全局最大值"""
    # 初始化数据收集器
    level_data = {
        'C9': {'升学率': [], '升学人数': [], '升学率增长': [], '留学质量': []},
        '985': {'升学率': [], '升学人数': [], '升学率增长': [], '留学质量': []},
        '211': {'升学率': [], '升学人数': [], '升学率增长': [], '留学质量': []},
        '其他': {'升学率': [], '升学人数': [], '升学率增长': [], '留学质量': []}
    }
    
    # 初始化全局最大值收集器
    all_values = {
        '升学率': [],
        '升学人数': [],
        '升学率增长': [],
        '留学质量': []
    }
    
    # 遍历所有学校数据
    for school_name, years_data in employment_data.items():
        # 确定学校层级
        level = _get_school_level_from_name(school_name)
        
        # 收集升学率数据
        rates = []
        for year_data in years_data:
            deep_info = year_data.get('employment_data', {}).get('深造情况', {})
            if deep_info and '总深造率' in deep_info:
                try:
                    # 处理百分号
                    rate_str = str(deep_info['总深造率']).strip('%')
                    rate = float(rate_str)
                    rates.append(rate)
                    all_values['升学率'].append(rate)
                except (ValueError, TypeError):
                    continue
        
        if rates:
            level_data[level]['升学率'].append(sum(rates) / len(rates))
        
        # 收集升学人数数据
        numbers = []
        for year_data in years_data:
            deep_info = year_data.get('employment_data', {}).get('深造情况', {})
            if deep_info:
                total = (deep_info.get('国内升学人数', 0) or 0) + (deep_info.get('出国留学人数', 0) or 0)
                if total > 0:
                    numbers.append(total)
                    all_values['升学人数'].append(total)
        
        if numbers:
            level_data[level]['升学人数'].append(sum(numbers) / len(numbers))
        
        # 收集升学率增长数据
        if len(rates) >= 2:
            growth_rates = []
            for i in range(1, len(rates)):
                if rates[i-1] > 0:
                    growth_rate = ((rates[i] - rates[i-1]) / rates[i-1]) * 100 if rates[i] > 0 else 0
                    growth_rates.append(growth_rate)
                    all_values['升学率增长'].append(growth_rate)
        
        if growth_rates:
            level_data[level]['升学率增长'].append(sum(growth_rates) / len(growth_rates))
        
        # 收集留学质量数据（美国留学占比）
        us_ratios = []
        for year_data in years_data:
            study_abroad = year_data.get('employment_data', {}).get('就业流向', {}).get('留学国家', [])
            if study_abroad:
                for country in study_abroad:
                    if country.get('国家') == '美国':
                        try:
                            # 处理百分号
                            ratio_str = str(country['占比']).strip('%')
                            ratio = float(ratio_str) / 100  # 转换为小数
                            us_ratios.append(ratio)
                            all_values['留学质量'].append(ratio)
                        except (ValueError, TypeError):
                            continue
        
        if us_ratios:
            level_data[level]['留学质量'].append(sum(us_ratios) / len(us_ratios))
    
    # 计算全局最大值
    global_max_values = {}
    for metric, values in all_values.items():
        if values:
            global_max_values[metric] = max(values)
        else:
            global_max_values[metric] = {
                '升学率': 30.0,  # 保守的最大值估计
                '升学人数': 500,
                '升学率增长': 10.0,
                '留学质量': 80.0
            }[metric]
    
    # 计算每个层级的平均值
    default_values = {}
    for level, metrics in level_data.items():
        default_values[level] = {}
        for metric, values in metrics.items():
            if values:
                default_values[level][metric] = sum(values) / len(values)
            else:
                default_values[level][metric] = {
                    '升学率': 5.0,
                    '升学人数': 50,
                    '升学率增长': 1.0,
                    '留学质量': 20.0
                }[metric]
    
    return default_values, global_max_values

def _get_school_level_from_name(school_name: str) -> str:
    """根据学校名称判断层级"""
    # 使用集合来避免重复
    c9_schools = set(city_level_map['c9'])
    _985_schools = set(city_level_map['985']) - c9_schools
    _211_schools = set(city_level_map['211']) - set(city_level_map['985'])

    if school_name in c9_schools:
        return 'C9'
    elif school_name in _985_schools:
        return '985'
    elif school_name in _211_schools:
        return '211'
    else:
        return '其他'

class AdvancedStudyScoreCalculator:
    """升学评分计算器"""
    
    def __init__(self, user_info: UserInfo, target_info: TargetInfo):
        """
        初始化评分计算器
        :param user_info: 用户信息
        :param target_info: 目标信息
        """
        self.user_info = user_info
        self.target_info = target_info
        self.employment_data = EMPLOYMENT_DATA  # 在实例中保存就业数据的引用
        
    def _get_description(self, dimension: str, score: float) -> str:
        """获取维度描述"""
        if score >= SCORE_LEVELS['high']['threshold']:
            return SCORE_LEVELS['high']['descriptions'][dimension]
        elif score >= SCORE_LEVELS['medium']['threshold']:
            return SCORE_LEVELS['medium']['descriptions'][dimension]
        return SCORE_LEVELS['low']['descriptions'][dimension]

    def calculate_total_score(self, school_info: SchoolInfo, employment_data: List[Dict]) -> Dict[str, Any]:
        """计算总分"""
        # 计算各维度得分
        rate = self.calculate_rate_score(school_info, employment_data)
        number = self.calculate_number_score(school_info, employment_data)
        growth = self.calculate_growth_score(school_info, employment_data)
        quality = self.calculate_quality_score(school_info, employment_data)
        
        dimension_scores = [
            {
                "name": "升学率",
                "score": rate['score'],
                "source": rate['source'],
                "weight": ADVANCED_STUDY_WEIGHTS["升学率"],
                "description": self._get_description("升学率", rate['score']),
                "weighted_score": rate['score'] * ADVANCED_STUDY_WEIGHTS["升学率"]
            },
            {
                "name": "升学人数",
                "score": number['score'],
                "source": number['source'],
                "weight": ADVANCED_STUDY_WEIGHTS["升学人数"],
                "description": self._get_description("升学人数", number['score']),
                "weighted_score": number['score'] * ADVANCED_STUDY_WEIGHTS["升学人数"]
            },
            {
                "name": "升学率增长",
                "score": growth['score'],
                "source": growth['source'],
                "weight": ADVANCED_STUDY_WEIGHTS["升学率增长"],
                "description": self._get_description("升学率增长", growth['score']),
                "weighted_score": growth['score'] * ADVANCED_STUDY_WEIGHTS["升学率增长"]
            },
            {
                "name": "留学质量",
                "score": quality['score'],
                "source": quality['source'],
                "weight": ADVANCED_STUDY_WEIGHTS["留学质量"],
                "description": self._get_description("留学质量", quality['score']),
                "weighted_score": quality['score'] * ADVANCED_STUDY_WEIGHTS["留学质量"]
            }
        ]
        
        # 计算总分
        total_score = sum(score["weighted_score"] for score in dimension_scores)
        
        return {
            "dimension_scores": dimension_scores,
            "total_score": total_score,
            "school_name": school_info.school_name
        }

    def _get_default_value(self, school: SchoolInfo, metric: str) -> float:
        """获取指定指标的默认值"""
        level = self._get_school_level(school)
        return DEFAULT_VALUES.get(level, {}).get(metric, 0.0)

    def _get_school_level(self, school: SchoolInfo) -> str:
        """获取学校层级"""
        # 使用集合来避免重复
        c9_schools = set(city_level_map['c9'])
        _985_schools = set(city_level_map['985']) - c9_schools
        _211_schools = set(city_level_map['211']) - set(city_level_map['985'])

        if school.school_name in c9_schools:
            return 'C9'
        elif school.school_name in _985_schools:
            return '985'
        elif school.school_name in _211_schools:
            return '211'
        else:
            return '其他'

    def _get_school_level_from_name(self, school_name: str) -> str:
        """根据学校名称判断层级"""
        # 使用集合来避免重复
        c9_schools = set(city_level_map['c9'])
        _985_schools = set(city_level_map['985']) - c9_schools
        _211_schools = set(city_level_map['211']) - set(city_level_map['985'])

        if school_name in c9_schools:
            return 'C9'
        elif school_name in _985_schools:
            return '985'
        elif school_name in _211_schools:
            return '211'
        else:
            return '其他'

    def calculate_rate_score(self, school_info: SchoolInfo, employment_data: List[Dict]) -> Dict:
        """计算升学率得分"""
        try:
            if employment_data:
                rates = []
                for year_data in employment_data:
                    deep_info = year_data.get('employment_data', {}).get('深造情况', {})
                    if deep_info and '总深造率' in deep_info:
                        try:
                            rate_str = str(deep_info['总深造率']).strip('%')
                            rate = float(rate_str)
                            rates.append(rate)
                        except (ValueError, TypeError):
                            continue
            
                if rates:
                    avg_rate = sum(rates) / len(rates)
                    return {
                        'score': min(100, avg_rate * 2),  # 升学率乘以2转换为百分制
                        'source': 'real'
                    }
            
            # 使用默认值
            return {
                'score': ADVANCED_STUDY_DEFAULTS['升学率'],
                'source': 'default'
            }
        except Exception as e:
            logger.error(f"计算升学率得分时出错: {str(e)}")
            return {
                'score': ADVANCED_STUDY_DEFAULTS['升学率'],
                'source': 'default'
            }

    def calculate_number_score(self, school_info: SchoolInfo, employment_data: List[Dict]) -> Dict:
        """计算升学人数得分"""
        try:
            if employment_data:
                numbers = []
                for year_data in employment_data:
                    deep_info = year_data.get('employment_data', {}).get('深造情况', {})
                    if deep_info:
                        total = (deep_info.get('国内升学人数', 0) or 0) + (deep_info.get('出国留学人数', 0) or 0)
                        if total > 0:
                            numbers.append(total)
            
                if numbers:
                    avg_number = sum(numbers) / len(numbers)
                    return {
                        'score': min(100, avg_number / 2),  # 每2人1分，最高100分
                        'source': 'real'
                    }
            
            # 使用默认值
            return {
                'score': ADVANCED_STUDY_DEFAULTS['升学人数'],
                'source': 'default'
            }
        except Exception as e:
            logger.error(f"计算升学人数得分时出错: {str(e)}")
            return {
                'score': ADVANCED_STUDY_DEFAULTS['升学人数'],
                'source': 'default'
            }

    def calculate_growth_score(self, school_info: SchoolInfo, employment_data: List[Dict]) -> Dict:
        """计算升学率增长得分"""
        try:
            if employment_data:
                rates = []
                for year_data in employment_data:
                    deep_info = year_data.get('employment_data', {}).get('深造情况', {})
                    if deep_info and '总深造率' in deep_info:
                        try:
                            rate_str = str(deep_info['总深造率']).strip('%')
                            rate = float(rate_str)
                            rates.append(rate)
                        except (ValueError, TypeError):
                            continue
            
            if len(rates) >= 2:
                growth_rates = []
                for i in range(1, len(rates)):
                    if rates[i-1] > 0:
                        growth_rate = ((rates[i] - rates[i-1]) / rates[i-1]) * 100
                        growth_rates.append(growth_rate)
            
            if growth_rates:
                avg_growth = sum(growth_rates) / len(growth_rates)
                return {
                    'score': min(100, max(0, 50 + avg_growth * 10)),  # 基准50分，每增长1%加10分
                    'source': 'calculated'
                }
        
            # 使用默认值
            return {
                'score': ADVANCED_STUDY_DEFAULTS['升学率增长'],
                'source': 'default'
            }
        except Exception as e:
            logger.error(f"计算升学率增长得分时出错: {str(e)}")
            return {
                'score': ADVANCED_STUDY_DEFAULTS['升学率增长'],
                'source': 'default'
            }

    def calculate_quality_score(self, school_info: SchoolInfo, employment_data: List[Dict]) -> Dict:
        """计算留学质量得分"""
        try:
            if employment_data:
                quality_scores = []
                for year_data in employment_data:
                    deep_info = year_data.get('employment_data', {}).get('深造情况', {})
                    if deep_info:
                        abroad_total = deep_info.get('出国留学人数', 0) or 0
                        us_total = deep_info.get('美国留学人数', 0) or 0
                        if abroad_total > 0:
                            us_ratio = (us_total / abroad_total) * 100
                            quality_scores.append(us_ratio)
            
            if quality_scores:
                avg_quality = sum(quality_scores) / len(quality_scores)
                return {
                    'score': min(100, avg_quality),  # 美国留学占比作为得分
                    'source': 'real'
                }
        
            # 使用默认值
            return {
                'score': ADVANCED_STUDY_DEFAULTS['留学质量'],
                'source': 'default'
            }
        except Exception as e:
            logger.error(f"计算留学质量得分时出错: {str(e)}")
            return {
                'score': ADVANCED_STUDY_DEFAULTS['留学质量'],
                'source': 'default'
            }

    def _get_rate_details(self, school: SchoolInfo, years_data: List[Dict]) -> Dict:
        """获取升学率详情"""
        details = {
            'values': {},  # 按年份存储的值
            'source': '',  # 数据来源说明
            'latest_value': None,  # 最终使用的值
        }
        
        # 获取所有年份的数据
        for year_data in years_data:
            year = year_data.get('year', '')
            deep_info = year_data.get('employment_data', {}).get('深造情况', {})
            if deep_info and '总深造率' in deep_info:
                try:
                    rate_str = str(deep_info['总深造率']).strip('%')
                    rate = float(rate_str)
                    details['values'][year] = f"{rate}%"
                except (ValueError, TypeError):
                    continue
        
        # 确定最终使用的值和来源
        sorted_years = sorted(details['values'].keys(), reverse=True)
        if sorted_years:  # 有本校数据
            latest_rate = float(details['values'][sorted_years[0]].strip('%'))
            details['latest_value'] = f"{latest_rate}%"
            details['source'] = '本校最新数据'
        else:  # 需要使用默认值
            level = self._get_school_level(school)
            median_rate = self._get_level_median_rate(level)
            if median_rate is not None:
                details['latest_value'] = f"{median_rate}%"
                details['source'] = f'{level}层级中位数'
            else:
                all_rates = self._get_all_schools_latest_rates()
                if all_rates:
                    median_rate = median(all_rates)
                    details['latest_value'] = f"{median_rate}%"
                    details['source'] = '全部学校中位数'
        
        return details

    def _get_number_details(self, school: SchoolInfo, years_data: List[Dict]) -> Dict:
        """获取升学人数详情"""
        details = {
            'values': {},
            'source': '',
            'latest_value': None,
        }
        
        # 获取所有年份的数据
        for year_data in years_data:
            year = year_data.get('year', '')
            deep_info = year_data.get('employment_data', {}).get('深造情况', {})
            if deep_info:
                total = (deep_info.get('国内升学人数', 0) or 0) + (deep_info.get('出国留学人数', 0) or 0)
                if total > 0:
                    details['values'][year] = total
        
        # 确定最终使用的值和来源
        sorted_years = sorted(details['values'].keys(), reverse=True)
        if sorted_years:  # 有本校数据
            details['latest_value'] = details['values'][sorted_years[0]]
            details['source'] = '本校最新数据'
        else:  # 需要使用默认值
            # 优先使用同层级中位数
            level = self._get_school_level(school)
            level_median = self._get_level_median_number(level)
            if level_median is not None:
                details['latest_value'] = level_median
                details['source'] = f'{level}层级中位数'
            else:
                # 如果同层级中位数不可用，使用全部学校中位数
                all_median = self._get_all_schools_median_number()
                if all_median is not None:
                    details['latest_value'] = all_median
                    details['source'] = '全部学校中位数'
        
        return details

    def _get_growth_details(self, school: SchoolInfo, years_data: List[Dict]) -> Dict:
        """获取升学率增长详情"""
        details = {
            'values': {},
            'source': '',
            'latest_value': None,
        }
        
        # 获取按年份排序的升学率数据
        rates_by_year = {}
        for year_data in years_data:
            year = year_data.get('year', '')
            deep_info = year_data.get('employment_data', {}).get('深造情况', {})
            if deep_info and '总深造率' in deep_info:
                try:
                    rate_str = str(deep_info['总深造率']).strip('%')
                    rate = float(rate_str)
                    rates_by_year[year] = rate
                except (ValueError, TypeError):
                    continue
        
        # 计算年度增长率
        sorted_years = sorted(rates_by_year.keys(), reverse=True)
        if len(sorted_years) >= 3:  # 有足够的历史数据
            latest_rate = rates_by_year[sorted_years[0]]
            oldest_rate = rates_by_year[sorted_years[2]]
            
            if oldest_rate > 0:
                growth_rate = (pow(latest_rate / oldest_rate, 1/3) - 1) * 100
                details['latest_value'] = f"{growth_rate:.1f}%"
                details['source'] = '本校三年复合增长率'
                
                # 计算各年份的同比增长率
                for i in range(len(sorted_years)-1):
                    current_year = sorted_years[i]
                    prev_year = sorted_years[i+1]
                    if rates_by_year[prev_year] > 0:
                        yearly_growth = ((rates_by_year[current_year] - rates_by_year[prev_year]) / rates_by_year[prev_year]) * 100
                        details['values'][current_year] = f"{yearly_growth:.1f}%"
        else:  # 数据不足，优先使用同层级平均增长率
            level = self._get_school_level(school)
            level_avg = self._get_level_avg_growth(level)
            if level_avg is not None:
                details['latest_value'] = f"{level_avg:.1f}%"
                details['source'] = f'{level}层级平均增长率'
            else:
                # 如果同层级平均值不可用，使用全部学校平均增长率
                all_avg = self._get_all_schools_avg_growth()
                if all_avg is not None:
                    details['latest_value'] = f"{all_avg:.1f}%"
                    details['source'] = '全部学校平均增长率'
        
        return details

    def _get_quality_details(self, school: SchoolInfo, years_data: List[Dict]) -> Dict:
        """获取升学质量详情（美国留学占比）"""
        details = {
            'values': {},  # 按年份存储的值
            'source': '',  # 数据来源说明
            'latest_value': None,  # 最终使用的值
        }
        
        # 获取所有年份的数据
        for year_data in years_data:
            year = year_data.get('year', '')
            study_abroad = year_data.get('employment_data', {}).get('就业流向', {}).get('留学国家', [])
            if study_abroad:
                for country in study_abroad:
                    if country.get('国家') == '美国':
                        try:
                            ratio_str = str(country['占比']).strip('%')
                            ratio = float(ratio_str)
                            details['values'][year] = f"{ratio}%"
                        except (ValueError, TypeError):
                            continue
        
        # 确定最终使用的值和来源
        sorted_years = sorted(details['values'].keys(), reverse=True)
        if sorted_years:  # 有本校数据
            details['latest_value'] = details['values'][sorted_years[0]]
            details['source'] = '本校最新数据'
        else:  # 需要使用默认值
            # 优先使用同层级中位数
            level = self._get_school_level(school)
            level_median = self._get_level_median_quality(level)
            if level_median is not None:
                details['latest_value'] = f"{level_median * 100}%"
                details['source'] = f'{level}层级中位数'
            else:
                # 如果同层级中位数不可用，使用全部学校中位数
                all_median = self._get_all_schools_median_quality()
                if all_median is not None:
                    details['latest_value'] = f"{all_median * 100}%"
                    details['source'] = '全部学校中位数'
        
        return details

    def _get_level_median_quality(self, level: str) -> float:
        """获取指定层级学校的美国留学占比中位数"""
        try:
            ratios = []
            for school_name, years_data in self.employment_data.items():
                if self._get_school_level_from_name(school_name) == level:
                    sorted_years = sorted(years_data, key=lambda x: x.get('year', ''), reverse=True)
                    latest_ratio = None
                    historical_ratios = []
                    
                    for year_data in sorted_years:
                        study_abroad = year_data.get('employment_data', {}).get('就业流向', {}).get('留学国家', [])
                        if study_abroad:
                            for country in study_abroad:
                                if country.get('国家') == '美国':
                                    try:
                                        ratio_str = str(country['占比']).strip('%')
                                        ratio = float(ratio_str) / 100
                                        if latest_ratio is None:
                                            latest_ratio = ratio
                                        historical_ratios.append(ratio)
                                    except (ValueError, TypeError):
                                        continue
                    
                    if latest_ratio is None and historical_ratios:
                        latest_ratio = sum(historical_ratios) / len(historical_ratios)
                    
                    if latest_ratio is not None:
                        ratios.append(latest_ratio)
            
            return median(ratios) if ratios else None
        except Exception as e:
            logger.error(f"获取{level}层级学校美国留学占比中位数时出错: {str(e)}")
            return None

    def _get_all_schools_median_number(self) -> float:
        """获取所有学校的升学人数中位数"""
        try:
            numbers = []
            for school_name, years_data in self.employment_data.items():
                # 获取最近一年的有效升学人数
                sorted_years = sorted(years_data, key=lambda x: x.get('year', ''), reverse=True)
                latest_number = None
                historical_numbers = []
                
                for year_data in sorted_years:
                    deep_info = year_data.get('employment_data', {}).get('深造情况', {})
                    if deep_info:
                        total = (deep_info.get('国内升学人数', 0) or 0) + (deep_info.get('出国留学人数', 0) or 0)
                        if total > 0:
                            if latest_number is None:
                                latest_number = total
                            historical_numbers.append(total)
                
                # 如果最近一年数据缺失，使用历史均值
                if latest_number is None and historical_numbers:
                    latest_number = sum(historical_numbers) / len(historical_numbers)
                
                if latest_number is not None:
                    numbers.append(latest_number)
            
            return median(numbers) if numbers else None
        except Exception as e:
            logger.error(f"获取所有学校升学人数中位数时出错: {str(e)}")
            return None

    def _get_all_schools_latest_numbers(self) -> List[float]:
        """获取所有学校最近一年的升学人数"""
        try:
            numbers = []
            for school_name, years_data in self.employment_data.items():
                sorted_years = sorted(years_data, key=lambda x: x.get('year', ''), reverse=True)
                latest_number = None
                historical_numbers = []
                
                for year_data in sorted_years:
                    deep_info = year_data.get('employment_data', {}).get('深造情况', {})
                    if deep_info:
                        total = (deep_info.get('国内升学人数', 0) or 0) + (deep_info.get('出国留学人数', 0) or 0)
                        if total > 0:
                            if latest_number is None:
                                latest_number = total
                            historical_numbers.append(total)
                
                if latest_number is None and historical_numbers:
                    latest_number = sum(historical_numbers) / len(historical_numbers)
                
                if latest_number is not None:
                    numbers.append(latest_number)
            
            return numbers
        except Exception as e:
            logger.error(f"获取所有学校升学人数时出错: {str(e)}")
            return []

    def _get_all_schools_median_quality(self) -> float:
        """获取所有学校的美国留学占比中位数"""
        try:
            ratios = []
            for school_name, years_data in self.employment_data.items():
                sorted_years = sorted(years_data, key=lambda x: x.get('year', ''), reverse=True)
                latest_ratio = None
                historical_ratios = []
                
                for year_data in sorted_years:
                    deep_info = year_data.get('employment_data', {}).get('深造情况', {})
                    study_abroad = year_data.get('employment_data', {}).get('就业流向', {}).get('留学国家', [])
                    
                    if deep_info and study_abroad:
                        total_abroad = deep_info.get('出国留学人数', 0) or 0
                        if total_abroad > 0:
                            for country in study_abroad:
                                if country.get('国家') == '美国':
                                    try:
                                        us_ratio = float(country['占比']) / 100
                                        if latest_ratio is None:
                                            latest_ratio = us_ratio
                                        historical_ratios.append(us_ratio)
                                    except (ValueError, TypeError):
                                        continue
                
                if latest_ratio is None and historical_ratios:
                    latest_ratio = sum(historical_ratios) / len(historical_ratios)
                
                if latest_ratio is not None:
                    ratios.append(latest_ratio)
            
            return median(ratios) if ratios else None
        except Exception as e:
            logger.error(f"获取所有学校美国留学占比中位数时出错: {str(e)}")
            return None

    def _get_all_schools_latest_quality(self) -> List[float]:
        """获取所有学校最近一年的美国留学占比"""
        try:
            ratios = []
            for school_name, years_data in self.employment_data.items():
                sorted_years = sorted(years_data, key=lambda x: x.get('year', ''), reverse=True)
                latest_ratio = None
                historical_ratios = []
                
                for year_data in sorted_years:
                    deep_info = year_data.get('employment_data', {}).get('深造情况', {})
                    study_abroad = year_data.get('employment_data', {}).get('就业流向', {}).get('留学国家', [])
                    
                    if deep_info and study_abroad:
                        total_abroad = deep_info.get('出国留学人数', 0) or 0
                        if total_abroad > 0:
                            for country in study_abroad:
                                if country.get('国家') == '美国':
                                    try:
                                        us_ratio = float(country['占比']) / 100
                                        if latest_ratio is None:
                                            latest_ratio = us_ratio
                                        historical_ratios.append(us_ratio)
                                    except (ValueError, TypeError):
                                        continue
                
                if latest_ratio is None and historical_ratios:
                    latest_ratio = sum(historical_ratios) / len(historical_ratios)
                
                if latest_ratio is not None:
                    ratios.append(latest_ratio)
            
            return ratios
        except Exception as e:
            logger.error(f"获取所有学校美国留学占比时出错: {str(e)}")
            return []

    def _get_all_schools_growth_rates(self) -> List[float]:
        """获取所有学校的升学率增长率"""
        try:
            growth_rates = []
            for school_name, years_data in self.employment_data.items():
                # 获取按年份排序的升学率数据
                rates_by_year = {}
                for year_data in years_data:
                    year = year_data.get('year', '')
                    deep_info = year_data.get('employment_data', {}).get('深造情况', {})
                    if deep_info and '总深造率' in deep_info:
                        try:
                            rate_str = str(deep_info['总深造率']).strip('%')
                            rate = float(rate_str)
                            rates_by_year[year] = rate
                        except (ValueError, TypeError):
                            continue
                
                # 计算三年复合增长率
                sorted_years = sorted(rates_by_year.keys(), reverse=True)
                if len(sorted_years) >= 3:
                    latest_rate = rates_by_year[sorted_years[0]]
                    oldest_rate = rates_by_year[sorted_years[2]]
                    
                    if oldest_rate > 0:  # 避免除以零
                        # 计算三年复合增长率
                        growth_rate = (pow(latest_rate / oldest_rate, 1/3) - 1) * 100
                        growth_rates.append(growth_rate)
            
            return growth_rates
        except Exception as e:
            logger.error(f"获取所有学校增长率时出错: {str(e)}")
            return []

    def _get_all_schools_avg_growth(self) -> float:
        """获取所有学校的平均增长率"""
        try:
            growth_rates = self._get_all_schools_growth_rates()
            if growth_rates:
                return sum(growth_rates) / len(growth_rates)
            return None
        except Exception as e:
            logger.error(f"获取所有学校平均增长率时出错: {str(e)}")
            return None

    def _get_level_avg_growth(self, level: str) -> float:
        """获取指定层级学校的平均增长率"""
        try:
            growth_rates = []
            for school_name, years_data in self.employment_data.items():
                if self._get_school_level_from_name(school_name) == level:
                    rates_by_year = {}
                    for year_data in years_data:
                        deep_info = year_data.get('employment_data', {}).get('深造情况', {})
                        if deep_info and '总深造率' in deep_info:
                            try:
                                rate_str = str(deep_info['总深造率']).strip('%')
                                rate = float(rate_str)
                                rates_by_year[year_data.get('year', '')] = rate
                            except (ValueError, TypeError):
                                continue
                    
                    # 计算三年复合增长率
                    sorted_years = sorted(rates_by_year.keys(), reverse=True)
                    if len(sorted_years) >= 3:
                        latest_rate = rates_by_year[sorted_years[0]]
                        oldest_rate = rates_by_year[sorted_years[2]]
                        
                        if oldest_rate > 0:
                            growth_rate = (pow(latest_rate / oldest_rate, 1/3) - 1) * 100
                            growth_rates.append(growth_rate)
            
            return sum(growth_rates) / len(growth_rates) if growth_rates else None
        except Exception as e:
            logger.error(f"获取{level}层级学校平均增长率时出错: {str(e)}")
            return None 