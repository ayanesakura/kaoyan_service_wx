import json
from typing import Dict, List, Any, Tuple, Optional
from loguru import logger
import numpy as np
from statistics import median
from collections import defaultdict

from wxcloudrun.beans.input_models import UserInfo, TargetInfo, SchoolInfo
from wxcloudrun.score_card.constants import (
    SATISFACTION_SCORE_WEIGHTS,
    SATISFACTION_SCORE_DEFAULTS,
    LEVEL_SCORES
)
from wxcloudrun.score_card.score_data_loader import (
    get_school_data,
    get_major_data,
    SCHOOL_DATA,
    MAJOR_DATA
)

class MajorScoreCalculator:
    """专业评分计算器"""
    
    def __init__(self, user_info: UserInfo, target_info: TargetInfo, target_schools: List[Tuple[str, str]]):
        """初始化专业评分计算器
        
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
        self.school_satisfaction_data = []
        self.major_satisfaction_data = []
        self.school_rank_data = []
        self.major_level_data = []
        
        # 初始化数据
        self._init_comparison_data()
        
        logger.info(f"专业评分计算器初始化完成，共有 {len(self.target_schools)} 个目标学校专业")
    
    def _init_comparison_data(self):
        """初始化比较候选集数据"""
        # 获取目标学校列表
        target_school_names = set(school_name for school_name, _ in self.target_schools)
        
        # 学校综合满意度数据 - 只包含目标学校
        for school_name in target_school_names:
            school_data = get_school_data(school_name)
            if school_data and school_data.overall_satisfaction is not None:
                self.school_satisfaction_data.append((school_name, school_data.overall_satisfaction))
        
        # 学校排名数据 - 只包含目标学校
        for school_name in target_school_names:
            school_data = get_school_data(school_name)
            if school_data and school_data.rank is not None:
                self.school_rank_data.append((school_name, school_data.rank))
        
        # 专业综合满意度数据 - 只包含目标学校专业
        for school_name, major_code in self.target_schools:
            major_data = get_major_data(school_name, major_code)
            if major_data and major_data.overall_satisfaction is not None:
                self.major_satisfaction_data.append(((school_name, major_code), major_data.overall_satisfaction))
        
        # 专业等级数据 - 只包含目标学校专业
        for school_name, major_code in self.target_schools:
            major_data = get_major_data(school_name, major_code)
            if major_data and major_data.level is not None:
                self.major_level_data.append(((school_name, major_code), major_data.level))
        
        logger.info(f"""比较候选集初始化完成:
- 学校综合满意度数据: {len(self.school_satisfaction_data)} 条
- 学校排名数据: {len(self.school_rank_data)} 条
- 专业综合满意度数据: {len(self.major_satisfaction_data)} 条
- 专业等级数据: {len(self.major_level_data)} 条
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
    
    def calculate_school_satisfaction_score(self, school_name: str) -> Dict[str, Any]:
        """计算学校综合满意度得分
        
        Args:
            school_name: 学校名称
            
        Returns:
            得分信息
        """
        school_data = get_school_data(school_name)
        
        if not school_data or school_data.overall_satisfaction is None:
            return {
                "score": SATISFACTION_SCORE_DEFAULTS["school_satisfaction"],
                "description": "学校综合满意度数据缺失",
                "percentile": None,
                "value": None
            }
        
        # 提取所有满意度值
        satisfaction_values = [s[1] for s in self.school_satisfaction_data]
        
        # 计算分位点
        percentile = self.calculate_percentile(
            school_data.overall_satisfaction, 
            satisfaction_values
        )
        
        # 映射到0-100分
        score = percentile
        
        # 生成描述
        if percentile >= 80:
            description = "学校综合满意度极高"
        elif percentile >= 60:
            description = "学校综合满意度较高"
        elif percentile >= 40:
            description = "学校综合满意度一般"
        elif percentile >= 20:
            description = "学校综合满意度较低"
        else:
            description = "学校综合满意度很低"
        
        return {
            "score": score,
            "description": description,
            "percentile": percentile,
            "value": school_data.overall_satisfaction
        }
    
    def calculate_major_satisfaction_score(self, school_name: str, major_code: str) -> Dict[str, Any]:
        """计算专业综合满意度得分
        
        Args:
            school_name: 学校名称
            major_code: 专业代码
            
        Returns:
            得分信息
        """
        major_data = get_major_data(school_name, major_code)
        
        if not major_data or major_data.overall_satisfaction is None:
            return {
                "score": SATISFACTION_SCORE_DEFAULTS["major_satisfaction"],
                "description": "专业综合满意度数据缺失",
                "percentile": None,
                "value": None
            }
        
        # 提取所有满意度值
        satisfaction_values = [m[1] for m in self.major_satisfaction_data]
        
        # 计算分位点
        percentile = self.calculate_percentile(
            major_data.overall_satisfaction, 
            satisfaction_values
        )
        
        # 映射到0-100分
        score = percentile
        
        # 生成描述
        if percentile >= 80:
            description = "专业综合满意度极高"
        elif percentile >= 60:
            description = "专业综合满意度较高"
        elif percentile >= 40:
            description = "专业综合满意度一般"
        elif percentile >= 20:
            description = "专业综合满意度较低"
        else:
            description = "专业综合满意度很低"
        
        return {
            "score": score,
            "description": description,
            "percentile": percentile,
            "value": major_data.overall_satisfaction
        }
    
    def calculate_school_reputation_score(self, school_name: str) -> Dict[str, Any]:
        """计算学校知名度得分
        
        Args:
            school_name: 学校名称
            
        Returns:
            得分信息
        """
        school_data = get_school_data(school_name)
        
        if not school_data or school_data.rank is None:
            return {
                "score": SATISFACTION_SCORE_DEFAULTS["school_reputation"],
                "description": "学校排名数据缺失",
                "percentile": None,
                "value": None
            }
        
        # 提取所有排名值
        rank_values = [r[1] for r in self.school_rank_data]
        
        # 计算分位点（排名越小越好，所以使用reverse=True）
        percentile = self.calculate_percentile(
            school_data.rank, 
            rank_values,
            reverse=True
        )
        
        # 映射到0-100分
        score = percentile
        
        # 生成描述
        if percentile >= 80:
            description = "学校排名极高"
        elif percentile >= 60:
            description = "学校排名较高"
        elif percentile >= 40:
            description = "学校排名一般"
        elif percentile >= 20:
            description = "学校排名较低"
        else:
            description = "学校排名很低"
        
        return {
            "score": score,
            "description": description,
            "percentile": percentile,
            "value": school_data.rank
        }
    
    def calculate_major_ranking_score(self, school_name: str, major_code: str) -> Dict[str, Any]:
        """计算专业排名得分
        
        Args:
            school_name: 学校名称
            major_code: 专业代码
            
        Returns:
            得分信息
        """
        major_data = get_major_data(school_name, major_code)
        
        if not major_data or major_data.level is None:
            return {
                "score": SATISFACTION_SCORE_DEFAULTS["major_ranking"],
                "description": "专业等级数据缺失",
                "percentile": None,
                "value": None
            }
        
        # 根据等级映射分数
        level = major_data.level
        score = LEVEL_SCORES.get(level, SATISFACTION_SCORE_DEFAULTS["major_ranking"])
        
        # 生成描述
        if level in ['A+']:
            description = "专业等级极高"
        elif level in ['A', 'A-']:
            description = "专业等级较高"
        elif level in ['B+', 'B']:
            description = "专业等级一般"
        else:
            description = "专业等级较低"
        
        return {
            "score": score,
            "description": description,
            "percentile": None,
            "value": level
        }
    
    def calculate_total_score(self, school_info: SchoolInfo) -> Dict[str, Any]:
        """计算专业评分
        
        Args:
            school_name: 学校名称
            major_code: 专业代码
            
        Returns:
            评分结果
        """
        school_name = school_info.school_name
        major_code = school_info.major_code
        # 计算各维度得分
        school_satisfaction = self.calculate_school_satisfaction_score(school_name)
        major_satisfaction = self.calculate_major_satisfaction_score(school_name, major_code)
        school_reputation = self.calculate_school_reputation_score(school_name)
        major_ranking = self.calculate_major_ranking_score(school_info.school_name, school_info.major_code)
        
        # 计算加权总分
        dimension_scores = [
            {
                "name": "学校综合满意度",
                "score": school_satisfaction["score"],
                "weight": SATISFACTION_SCORE_WEIGHTS["school_satisfaction"],
                "weighted_score": school_satisfaction["score"] * SATISFACTION_SCORE_WEIGHTS["school_satisfaction"],
                "description": school_satisfaction["description"],
                "percentile": school_satisfaction["percentile"],
                "value": school_satisfaction["value"]
            },
            {
                "name": "专业综合满意度",
                "score": major_satisfaction["score"],
                "weight": SATISFACTION_SCORE_WEIGHTS["major_satisfaction"],
                "weighted_score": major_satisfaction["score"] * SATISFACTION_SCORE_WEIGHTS["major_satisfaction"],
                "description": major_satisfaction["description"],
                "percentile": major_satisfaction["percentile"],
                "value": major_satisfaction["value"]
            },
            {
                "name": "学校知名度",
                "score": school_reputation["score"],
                "weight": SATISFACTION_SCORE_WEIGHTS["school_reputation"],
                "weighted_score": school_reputation["score"] * SATISFACTION_SCORE_WEIGHTS["school_reputation"],
                "description": school_reputation["description"],
                "percentile": school_reputation["percentile"],
                "value": school_reputation["value"]
            },
            {
                "name": "专业排名",
                "score": major_ranking["score"],
                "weight": SATISFACTION_SCORE_WEIGHTS["major_ranking"],
                "weighted_score": major_ranking["score"] * SATISFACTION_SCORE_WEIGHTS["major_ranking"],
                "description": major_ranking["description"],
                "percentile": major_ranking["percentile"],
                "value": major_ranking["value"]
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
        
        if not self.target_schools:
            logger.warning("没有目标学校和专业，无法计算评分")
            return results
        
        for school_name, major_code in self.target_schools:
            try:
                score_result = self.calculate_score(school_name, major_code)
                results.append(score_result)
            except Exception as e:
                logger.error(f"计算 {school_name} - {major_code} 的专业评分时出错: {str(e)}")
                # 创建一个默认的评分结果
                major_data = get_major_data(school_name, major_code)
                results.append({
                    "dimension_scores": [],
                    "total_score": 0,
                    "school_name": school_name,
                    "major_code": major_code,
                    "major_name": major_data.major_name if major_data else None
                })
        
        # 按总分排序
        results.sort(key=lambda x: x["total_score"], reverse=True)
        
        return results 