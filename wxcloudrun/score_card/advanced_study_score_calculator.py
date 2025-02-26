from loguru import logger
from wxcloudrun.score_card.constants import (
    ADVANCED_STUDY_SCORE_WEIGHTS,
    ADVANCED_STUDY_SCORE_DEFAULTS,
    ADVANCED_STUDY_LEVELS,
    SCHOOL_LEVELS,
    SCORE_LEVELS
)
from wxcloudrun.utils.file_util import CITY_LEVEL_MAP
from wxcloudrun.beans.input_models import UserInfo, TargetInfo, SchoolInfo
import numpy as np
from typing import Dict, List, Any, Tuple
from statistics import median
from collections import defaultdict
import scipy.stats as stats
import json
from wxcloudrun.score_card.score_data_loader import (
    get_school_data,
    get_major_data,
    SCHOOL_DATA,
    MAJOR_DATA
)



class AdvancedStudyScoreCalculator:
    """升学评分计算器"""
    
    def __init__(self, user_info: UserInfo, target_info: TargetInfo, target_schools: List[Tuple[str, str]]):
        """初始化升学评分计算器
        
        Args:
            user_info: 用户信息
            target_info: 目标信息
            target_schools: 目标学校和专业列表，格式为[(school_name, major_code),...]
        """
        self.user_info = user_info
        self.target_info = target_info
        
        # 存储所有需要参与计算的学校名称和专业代码
        self.target_schools = target_schools
        
        # 初始化比较候选集
        self.further_study_rate_data = []
        self.further_study_number_data = []
        self.abroad_study_ratio_data = []
        self.us_study_ratio_data = []
        
        # 初始化数据
        self._init_comparison_data()
        
        logger.info(f"升学评分计算器初始化完成，共有 {len(self.target_schools)} 个目标学校专业")
    
    def _init_comparison_data(self):
        """初始化比较候选集数据"""
        # 获取目标学校列表
        target_school_names = set(school_name for school_name, _ in self.target_schools)
        
        # 升学率数据 - 只包含目标学校
        for school_name in target_school_names:
            school_data = get_school_data(school_name)
            if school_data and school_data.further_study_rate is not None:
                self.further_study_rate_data.append((school_name, school_data.further_study_rate))
        
        # 升学人数数据 - 只包含目标学校
        for school_name in target_school_names:
            school_data = get_school_data(school_name)
            if school_data and school_data.further_study_number is not None:
                self.further_study_number_data.append((school_name, school_data.further_study_number))
        
        # 出国留学占比数据 - 只包含目标学校
        for school_name in target_school_names:
            school_data = get_school_data(school_name)
            if school_data and school_data.abroad_study_ratio is not None:
                self.abroad_study_ratio_data.append((school_name, school_data.abroad_study_ratio))
        
        # 美国留学占比数据 - 只包含目标学校
        for school_name in target_school_names:
            school_data = get_school_data(school_name)
            if school_data and school_data.us_study_ratio is not None:
                self.us_study_ratio_data.append((school_name, school_data.us_study_ratio))
        
        logger.info(f"""比较候选集初始化完成:
- 升学率数据: {len(self.further_study_rate_data)} 条
- 升学人数数据: {len(self.further_study_number_data)} 条
- 出国留学占比数据: {len(self.abroad_study_ratio_data)} 条
- 美国留学占比数据: {len(self.us_study_ratio_data)} 条
        """)
    
    def calculate_percentile(self, value: float, data_list: List[float], reverse: bool = False) -> float:
        """计算分位点
        
        Args:
            value: 目标值
            data_list: 数据列表
            reverse: 是否反向计算（值越小越好）
            
        Returns:
            分位点(0-100)
        """
        if not data_list:
            return 50.0  # 默认中位数
        
        # 排序数据
        sorted_data = sorted(data_list)
        
        # 计算分位点
        if reverse:
            # 值越小越好
            percentile = 100 - (sum(1 for x in sorted_data if x <= value) / len(sorted_data) * 100)
        else:
            # 值越大越好
            percentile = sum(1 for x in sorted_data if x <= value) / len(sorted_data) * 100
        
        return percentile
    
    def calculate_further_study_rate_score(self, school_name: str) -> Dict[str, Any]:
        """计算升学率得分
        
        Args:
            school_name: 学校名称
            
        Returns:
            得分信息
        """
        school_data = get_school_data(school_name)
        
        if not school_data or school_data.further_study_rate is None:
            return {
                "score": ADVANCED_STUDY_SCORE_DEFAULTS["further_study_rate"],
                "description": "升学率数据缺失",
                "percentile": None,
                "value": None
            }
        
        # 提取所有升学率值
        rate_values = [r[1] for r in self.further_study_rate_data]
        
        # 计算分位点
        percentile = self.calculate_percentile(
            school_data.further_study_rate, 
            rate_values
        )
        
        # 映射到0-100分
        score = percentile
        
        # 生成描述
        for level, info in sorted(ADVANCED_STUDY_LEVELS.items(), key=lambda x: x[1]['threshold'], reverse=True):
            if percentile >= info['threshold']:
                description = info['descriptions']['升学率']
                break
        else:
            description = "升学率数据异常"
        
        return {
            "score": score,
            "description": description,
            "percentile": percentile,
            "value": school_data.further_study_rate
        }
    
    def calculate_further_study_number_score(self, school_name: str) -> Dict[str, Any]:
        """计算升学人数得分
        
        Args:
            school_name: 学校名称
            
        Returns:
            得分信息
        """
        school_data = get_school_data(school_name)
        
        if not school_data or school_data.further_study_number is None:
            return {
                "score": ADVANCED_STUDY_SCORE_DEFAULTS["further_study_number"],
                "description": "升学人数数据缺失",
                "percentile": None,
                "value": None
            }
        
        # 提取所有升学人数值
        number_values = [n[1] for n in self.further_study_number_data]
        
        # 计算分位点
        percentile = self.calculate_percentile(
            school_data.further_study_number, 
            number_values
        )
        
        # 映射到0-100分
        score = percentile
        
        # 生成描述
        for level, info in sorted(ADVANCED_STUDY_LEVELS.items(), key=lambda x: x[1]['threshold'], reverse=True):
            if percentile >= info['threshold']:
                description = info['descriptions']['升学人数']
                break
        else:
            description = "升学人数数据异常"
        
        return {
            "score": score,
            "description": description,
            "percentile": percentile,
            "value": school_data.further_study_number
        }
    
    def calculate_abroad_study_ratio_score(self, school_name: str) -> Dict[str, Any]:
        """计算出国留学占比得分
        
        Args:
            school_name: 学校名称
            
        Returns:
            得分信息
        """
        school_data = get_school_data(school_name)
        
        if not school_data or school_data.abroad_study_ratio is None:
            return {
                "score": ADVANCED_STUDY_SCORE_DEFAULTS["abroad_study_ratio"],
                "description": "出国留学占比数据缺失",
                "percentile": None,
                "value": None
            }
        
        # 提取所有出国留学占比值
        abroad_values = [a[1] for a in self.abroad_study_ratio_data]
        
        # 计算分位点
        percentile = self.calculate_percentile(
            school_data.abroad_study_ratio, 
            abroad_values
        )
        
        # 映射到0-100分
        score = percentile
        
        # 生成描述
        for level, info in sorted(ADVANCED_STUDY_LEVELS.items(), key=lambda x: x[1]['threshold'], reverse=True):
            if percentile >= info['threshold']:
                description = info['descriptions']['出国留学占比']
                break
        else:
            description = "出国留学占比数据异常"
        
        return {
            "score": score,
            "description": description,
            "percentile": percentile,
            "value": school_data.abroad_study_ratio
        }
    
    def calculate_us_study_ratio_score(self, school_name: str) -> Dict[str, Any]:
        """计算美国留学占比得分
        
        Args:
            school_name: 学校名称
            
        Returns:
            得分信息
        """
        school_data = get_school_data(school_name)
        
        if not school_data or school_data.us_study_ratio is None:
            return {
                "score": ADVANCED_STUDY_SCORE_DEFAULTS["us_study_ratio"],
                "description": "美国留学占比数据缺失",
                "percentile": None,
                "value": None
            }
        
        # 提取所有美国留学占比值
        us_values = [u[1] for u in self.us_study_ratio_data]
        
        # 计算分位点
        percentile = self.calculate_percentile(
            school_data.us_study_ratio, 
            us_values
        )
        
        # 映射到0-100分
        score = percentile
        
        # 生成描述
        for level, info in sorted(ADVANCED_STUDY_LEVELS.items(), key=lambda x: x[1]['threshold'], reverse=True):
            if percentile >= info['threshold']:
                description = info['descriptions']['美国留学占比']
                break
        else:
            description = "美国留学占比数据异常"
        
        return {
            "score": score,
            "description": description,
            "percentile": percentile,
            "value": school_data.us_study_ratio
        }
    
    def calculate_total_score(self, school_info: SchoolInfo) -> Dict[str, Any]:
        """计算升学评分
        
        Args:
            school_name: 学校名称
            major_code: 专业代码
            
        Returns:
            评分结果
        """
        school_name = school_info.school_name
        major_code = school_info.major_code
        # 计算各维度得分
        further_study_rate = self.calculate_further_study_rate_score(school_name)
        further_study_number = self.calculate_further_study_number_score(school_name)
        abroad_study_ratio = self.calculate_abroad_study_ratio_score(school_info.school_name)
        us_study_ratio = self.calculate_us_study_ratio_score(school_info.school_name)
        
        # 计算加权总分
        dimension_scores = [
            {
                "name": "升学率",
                "score": further_study_rate["score"],
                "weight": ADVANCED_STUDY_SCORE_WEIGHTS["further_study_rate"],
                "weighted_score": further_study_rate["score"] * ADVANCED_STUDY_SCORE_WEIGHTS["further_study_rate"],
                "description": further_study_rate["description"],
                "percentile": further_study_rate["percentile"],
                "value": further_study_rate["value"]
            },
            {
                "name": "升学人数",
                "score": further_study_number["score"],
                "weight": ADVANCED_STUDY_SCORE_WEIGHTS["further_study_number"],
                "weighted_score": further_study_number["score"] * ADVANCED_STUDY_SCORE_WEIGHTS["further_study_number"],
                "description": further_study_number["description"],
                "percentile": further_study_number["percentile"],
                "value": further_study_number["value"]
            },
            {
                "name": "出国留学占比",
                "score": abroad_study_ratio["score"],
                "weight": ADVANCED_STUDY_SCORE_WEIGHTS["abroad_study_ratio"],
                "weighted_score": abroad_study_ratio["score"] * ADVANCED_STUDY_SCORE_WEIGHTS["abroad_study_ratio"],
                "description": abroad_study_ratio["description"],
                "percentile": abroad_study_ratio["percentile"],
                "value": abroad_study_ratio["value"]
            },
            {
                "name": "美国留学占比",
                "score": us_study_ratio["score"],
                "weight": ADVANCED_STUDY_SCORE_WEIGHTS["us_study_ratio"],
                "weighted_score": us_study_ratio["score"] * ADVANCED_STUDY_SCORE_WEIGHTS["us_study_ratio"],
                "description": us_study_ratio["description"],
                "percentile": us_study_ratio["percentile"],
                "value": us_study_ratio["value"]
            }
        ]
        
        total_score = sum(item["weighted_score"] for item in dimension_scores)
        major_data = get_major_data(school_name, major_code)
        
        return {
            "dimension_scores": dimension_scores,
            "total_score": total_score,
            "school_name": school_name,
            "major_code": major_code,
            "major_name": major_data.major_name if major_data else None
        }
    
    def calculate_all_scores(self) -> List[Dict[str, Any]]:
        """计算所有目标学校专业的评分
        
        Returns:
            所有评分结果列表
        """
        results = []
        
        for school_name, major_code in self.target_schools:
            try:
                score_result = self.calculate_score(school_name, major_code)
                results.append(score_result)
            except Exception as e:
                logger.error(f"计算 {school_name} - {major_code} 的升学评分时出错: {str(e)}")
                continue
        
        # 按总分排序
        results.sort(key=lambda x: x["total_score"], reverse=True)
        
        return results

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
        return percentile  # 返回实际的百分位数
    except Exception as e:
        logger.error(f"计算分位数得分时出错: {str(e)}")
        return 0

def calculate_school_stats(employment_data: Dict[str, List[Dict]]):
    """预计算所有学校的统计数据"""
    global SCHOOL_STATS
    
    # 收集升学率数据
    all_rates = []
    for school_name, years_data in employment_data.items():
        school_rates = []
        for year_data in years_data:
            deep_info = year_data.get('employment_data', {}).get('深造情况', {})
            if deep_info and '总深造率' in deep_info:
                try:
                    rate_str = str(deep_info['总深造率']).strip('%')
                    rate = float(rate_str)
                    rate = rate / 100 if rate > 1 else rate
                    school_rates.append(rate)
                except (ValueError, TypeError):
                    continue
        if school_rates:
            all_rates.append(sum(school_rates) / len(school_rates))
    
    # 收集留学质量数据
    all_qualities = []
    for school_name, years_data in employment_data.items():
        school_qualities = []
        for year_data in years_data:
            try:
                flow_info = year_data.get('employment_data', {}).get('就业流向', {})
                study_abroad = flow_info.get('留学国家', [])
                if study_abroad:  # 添加空值检查
                    for country in study_abroad:
                        if country and isinstance(country, dict) and country.get('国家') == '美国':  # 增加类型检查
                            try:
                                us_ratio = float(country.get('占比', 0))
                                us_ratio = us_ratio / 100 if us_ratio > 1 else us_ratio
                                school_qualities.append(us_ratio)
                            except (ValueError, TypeError):
                                continue
            except Exception as e:
                logger.error(f"处理学校 {school_name} 的留学数据时出错: {str(e)}")
                continue
                
        if school_qualities:
            all_qualities.append(sum(school_qualities) / len(school_qualities))
    
    # 计算统计信息
    SCHOOL_STATS['rate'] = {
        'all_rates': all_rates,
        'stats': {
            'min': min(all_rates) if all_rates else 0,
            'max': max(all_rates) if all_rates else 0,
            'avg': sum(all_rates) / len(all_rates) if all_rates else 0,
            'total_schools': len(all_rates)
        }
    }
    
    SCHOOL_STATS['quality'] = {
        'all_qualities': all_qualities,
        'stats': {
            'min': min(all_qualities) if all_qualities else 0,
            'max': max(all_qualities) if all_qualities else 0,
            'avg': sum(all_qualities) / len(all_qualities) if all_qualities else 0,
            'total_schools': len(all_qualities)
        }
    }
    
    logger.info(f"成功计算统计数据，共有 {len(all_rates)} 所学校的升学率数据，{len(all_qualities)} 所学校的留学质量数据") 