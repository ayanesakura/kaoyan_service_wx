import json
from typing import Dict, List, Any, Tuple, Optional
from loguru import logger
from statistics import median
import numpy as np
from scipy import stats
from collections import defaultdict
from wxcloudrun.beans.input_models import UserInfo, TargetInfo, SchoolInfo
from wxcloudrun.utils.file_util import CITY_LEVEL_MAP
from wxcloudrun.score_card.constants import (
    NON_SYSTEM_EMPLOYMENT_SCORE_WEIGHTS,
    NON_SYSTEM_EMPLOYMENT_SCORE_DEFAULTS,
    NON_SYSTEM_EMPLOYMENT_LEVELS
)
from wxcloudrun.score_card.score_data_loader import (
    get_school_data,
    get_major_data,
    SCHOOL_DATA,
    MAJOR_DATA
)

# 修改默认值定义
DEFAULT_VALUES = NON_SYSTEM_EMPLOYMENT_SCORE_DEFAULTS

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
    
    def __init__(self, user_info: UserInfo, target_info: TargetInfo, target_schools: List[Tuple[str, str]]):
        """初始化非体制就业评分计算器
        
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
        self.school_employment_data = []
        self.school_satisfaction_data = []
        self.major_satisfaction_data = []
        
        # 初始化数据
        self._init_comparison_data()
        
        logger.info(f"非体制就业评分计算器初始化完成，共有 {len(self.target_schools)} 个目标学校专业")
    
    def _init_comparison_data(self):
        """初始化比较候选集数据"""
        # 获取目标学校列表
        target_school_names = set(school_name for school_name, _ in self.target_schools)
        
        # 学校就业率数据 - 只包含目标学校
        for school_name in target_school_names:
            school_data = get_school_data(school_name)
            if school_data and school_data.employment_ratio is not None:
                self.school_employment_data.append((school_name, school_data.employment_ratio))
        
        # 学校环境满意度数据 - 只包含目标学校
        for school_name in target_school_names:
            school_data = get_school_data(school_name)
            if school_data and school_data.environment_satisfaction is not None:
                self.school_satisfaction_data.append((school_name, school_data.environment_satisfaction))
        
        # 专业就业满意度数据 - 只包含目标学校专业
        for school_name, major_code in self.target_schools:
            major_data = get_major_data(school_name, major_code)
            if major_data and major_data.employment_satisfaction is not None:
                self.major_satisfaction_data.append(((school_name, major_code), major_data.employment_satisfaction))
        
        logger.info(f"""比较候选集初始化完成:
- 学校就业率数据: {len(self.school_employment_data)} 条
- 学校环境满意度数据: {len(self.school_satisfaction_data)} 条
- 专业就业满意度数据: {len(self.major_satisfaction_data)} 条
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
    
    def calculate_employment_rate_score(self, school_name: str) -> Dict[str, Any]:
        """计算就业率得分
        
        Args:
            school_name: 学校名称
            
        Returns:
            得分信息
        """
        school_data = get_school_data(school_name)
        
        if not school_data or school_data.employment_ratio is None:
            return {
                "score": NON_SYSTEM_EMPLOYMENT_SCORE_DEFAULTS["employment_rate"],
                "description": "就业率数据缺失",
                "percentile": None,
                "value": None
            }
        
        # 提取所有就业率值
        employment_values = [e[1] for e in self.school_employment_data]
        
        # 计算分位点
        percentile = self.calculate_percentile(
            school_data.employment_ratio, 
            employment_values
        )
        
        # 映射到0-100分
        score = percentile
        
        # 生成描述
        for level, info in sorted(NON_SYSTEM_EMPLOYMENT_LEVELS.items(), key=lambda x: x[1]['threshold'], reverse=True):
            if percentile >= info['threshold']:
                description = info['descriptions']['就业率']
                break
        else:
            description = "就业率数据异常"
        
        return {
            "score": score,
            "description": description,
            "percentile": percentile,
            "value": school_data.employment_ratio
        }
    
    def calculate_school_satisfaction_score(self, school_name: str) -> Dict[str, Any]:
        """计算学校环境满意度得分
        
        Args:
            school_name: 学校名称
            
        Returns:
            得分信息
        """
        school_data = get_school_data(school_name)
        
        if not school_data or school_data.environment_satisfaction is None:
            return {
                "score": NON_SYSTEM_EMPLOYMENT_SCORE_DEFAULTS["school_satisfaction"],
                "description": "学校环境满意度数据缺失",
                "percentile": None,
                "value": None
            }
        
        # 提取所有满意度值
        satisfaction_values = [s[1] for s in self.school_satisfaction_data]
        
        # 计算分位点
        percentile = self.calculate_percentile(
            school_data.environment_satisfaction, 
            satisfaction_values
        )
        
        # 映射到0-100分
        score = percentile
        
        # 生成描述
        for level, info in sorted(NON_SYSTEM_EMPLOYMENT_LEVELS.items(), key=lambda x: x[1]['threshold'], reverse=True):
            if percentile >= info['threshold']:
                description = info['descriptions']['学校满意度']
                break
        else:
            description = "学校环境满意度数据异常"
        
        return {
            "score": score,
            "description": description,
            "percentile": percentile,
            "value": school_data.environment_satisfaction
        }
    
    def calculate_major_satisfaction_score(self, school_name: str, major_code: str) -> Dict[str, Any]:
        """计算专业就业满意度得分
        
        Args:
            school_name: 学校名称
            major_code: 专业代码
            
        Returns:
            得分信息
        """
        major_data = get_major_data(school_name, major_code)
        
        if not major_data or major_data.employment_satisfaction is None:
            return {
                "score": NON_SYSTEM_EMPLOYMENT_SCORE_DEFAULTS["major_satisfaction"],
                "description": "专业就业满意度数据缺失",
                "percentile": None,
                "value": None
            }
        
        # 提取所有满意度值
        satisfaction_values = [m[1] for m in self.major_satisfaction_data]
        
        # 计算分位点
        percentile = self.calculate_percentile(
            major_data.employment_satisfaction, 
            satisfaction_values
        )
        
        # 映射到0-100分
        score = percentile
        
        # 生成描述
        for level, info in sorted(NON_SYSTEM_EMPLOYMENT_LEVELS.items(), key=lambda x: x[1]['threshold'], reverse=True):
            if percentile >= info['threshold']:
                description = info['descriptions']['专业满意度']
                break
        else:
            description = "专业就业满意度数据异常"
        
        return {
            "score": score,
            "description": description,
            "percentile": percentile,
            "value": major_data.employment_satisfaction
        }
    
    def calculate_total_score(self, school_info: SchoolInfo) -> Dict[str, Any]:
        """计算非体制就业评分
        
        Args:
            school_name: 学校名称
            major_code: 专业代码
            
        Returns:
            评分结果
        """
        school_name = school_info.school_name
        major_code = school_info.major_code
        # 计算各维度得分
        employment_rate = self.calculate_employment_rate_score(school_name)
        school_satisfaction = self.calculate_school_satisfaction_score(school_name)
        major_satisfaction = self.calculate_major_satisfaction_score(school_name, major_code)
        
        # 计算加权总分
        dimension_scores = [
            {
                "name": "就业率",
                "score": employment_rate["score"],
                "weight": NON_SYSTEM_EMPLOYMENT_SCORE_WEIGHTS["employment_rate"],
                "weighted_score": employment_rate["score"] * NON_SYSTEM_EMPLOYMENT_SCORE_WEIGHTS["employment_rate"],
                "description": employment_rate["description"],
                "percentile": employment_rate["percentile"],
                "value": employment_rate["value"]
            },
            {
                "name": "学校环境满意度",
                "score": school_satisfaction["score"],
                "weight": NON_SYSTEM_EMPLOYMENT_SCORE_WEIGHTS["school_satisfaction"],
                "weighted_score": school_satisfaction["score"] * NON_SYSTEM_EMPLOYMENT_SCORE_WEIGHTS["school_satisfaction"],
                "description": school_satisfaction["description"],
                "percentile": school_satisfaction["percentile"],
                "value": school_satisfaction["value"]
            },
            {
                "name": "专业就业满意度",
                "score": major_satisfaction["score"],
                "weight": NON_SYSTEM_EMPLOYMENT_SCORE_WEIGHTS["major_satisfaction"],
                "weighted_score": major_satisfaction["score"] * NON_SYSTEM_EMPLOYMENT_SCORE_WEIGHTS["major_satisfaction"],
                "description": major_satisfaction["description"],
                "percentile": major_satisfaction["percentile"],
                "value": major_satisfaction["value"]
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
                logger.error(f"计算 {school_name} - {major_code} 的非体制就业评分时出错: {str(e)}")
                continue
        
        # 按总分排序
        results.sort(key=lambda x: x["total_score"], reverse=True)
        
        return results