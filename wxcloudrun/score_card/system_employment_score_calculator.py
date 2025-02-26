import json
from typing import Dict, List, Any, Tuple, Optional
from loguru import logger
from statistics import median
import numpy as np
from collections import defaultdict
from wxcloudrun.beans.input_models import UserInfo, TargetInfo, SchoolInfo
from wxcloudrun.score_card.constants import (
    SYSTEM_EMPLOYMENT_SCORE_WEIGHTS,
    SYSTEM_EMPLOYMENT_SCORE_DEFAULTS,
    SYSTEM_EMPLOYMENT_LEVELS
)
from wxcloudrun.score_card.score_data_loader import (
    get_school_data,
    get_major_data,
    SCHOOL_DATA,
    MAJOR_DATA
)

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



class SystemEmploymentScoreCalculator:
    """体制内就业评分计算器"""
    
    def __init__(self, user_info: UserInfo, target_info: TargetInfo, target_schools: List[Tuple[str, str]]):
        """初始化体制内就业评分计算器
        
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
        self.civil_servant_data = []
        self.institution_data = []
        self.state_owned_data = []
        
        # 初始化数据
        self._init_comparison_data()
        
        logger.info(f"体制内就业评分计算器初始化完成，共有 {len(self.target_schools)} 个目标学校专业")
    
    def _init_comparison_data(self):
        """初始化比较候选集数据"""
        # 获取目标学校列表
        target_school_names = set(school_name for school_name, _ in self.target_schools)
        
        # 公务员占比数据 - 只包含目标学校
        for school_name in target_school_names:
            school_data = get_school_data(school_name)
            if school_data and school_data.civil_servant_ratio is not None:
                self.civil_servant_data.append((school_name, school_data.civil_servant_ratio))
        
        # 事业单位占比数据 - 只包含目标学校
        for school_name in target_school_names:
            school_data = get_school_data(school_name)
            if school_data and school_data.institution_ratio is not None:
                self.institution_data.append((school_name, school_data.institution_ratio))
        
        # 国企占比数据 - 只包含目标学校
        for school_name in target_school_names:
            school_data = get_school_data(school_name)
            if school_data and school_data.state_owned_ratio is not None:
                self.state_owned_data.append((school_name, school_data.state_owned_ratio))
        
        logger.info(f"""比较候选集初始化完成:
- 公务员占比数据: {len(self.civil_servant_data)} 条
- 事业单位占比数据: {len(self.institution_data)} 条
- 国企占比数据: {len(self.state_owned_data)} 条
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
    
    def calculate_civil_servant_score(self, school_name: str) -> Dict[str, Any]:
        """计算公务员占比得分
        
        Args:
            school_name: 学校名称
            
        Returns:
            得分信息
        """
        school_data = get_school_data(school_name)
        
        if not school_data or school_data.civil_servant_ratio is None:
            return {
                "score": SYSTEM_EMPLOYMENT_SCORE_DEFAULTS["civil_servant"],
                "description": "公务员占比数据缺失",
                "percentile": None,
                "value": None
            }
        
        # 提取所有公务员占比值
        civil_servant_values = [c[1] for c in self.civil_servant_data]
        
        # 计算分位点
        percentile = self.calculate_percentile(
            school_data.civil_servant_ratio, 
            civil_servant_values
        )
        
        # 映射到0-100分
        score = percentile
        
        # 生成描述
        for level, info in sorted(SYSTEM_EMPLOYMENT_LEVELS.items(), key=lambda x: x[1]['threshold'], reverse=True):
            if percentile >= info['threshold']:
                description = info['descriptions']['公务员占比']
                break
        else:
            description = "公务员占比数据异常"
        
        return {
            "score": score,
            "description": description,
            "percentile": percentile,
            "value": school_data.civil_servant_ratio
        }
    
    def calculate_institution_score(self, school_name: str) -> Dict[str, Any]:
        """计算事业单位占比得分
        
        Args:
            school_name: 学校名称
            
        Returns:
            得分信息
        """
        school_data = get_school_data(school_name)
        
        if not school_data or school_data.institution_ratio is None:
            return {
                "score": SYSTEM_EMPLOYMENT_SCORE_DEFAULTS["institution"],
                "description": "事业单位占比数据缺失",
                "percentile": None,
                "value": None
            }
        
        # 提取所有事业单位占比值
        institution_values = [i[1] for i in self.institution_data]
        
        # 计算分位点
        percentile = self.calculate_percentile(
            school_data.institution_ratio, 
            institution_values
        )
        
        # 映射到0-100分
        score = percentile
        
        # 生成描述
        for level, info in sorted(SYSTEM_EMPLOYMENT_LEVELS.items(), key=lambda x: x[1]['threshold'], reverse=True):
            if percentile >= info['threshold']:
                description = info['descriptions']['事业单位占比']
                break
        else:
            description = "事业单位占比数据异常"
        
        return {
            "score": score,
            "description": description,
            "percentile": percentile,
            "value": school_data.institution_ratio
        }
    
    def calculate_state_owned_score(self, school_name: str) -> Dict[str, Any]:
        """计算国企占比得分
        
        Args:
            school_name: 学校名称
            
        Returns:
            得分信息
        """
        school_data = get_school_data(school_name)
        
        if not school_data or school_data.state_owned_ratio is None:
            return {
                "score": SYSTEM_EMPLOYMENT_SCORE_DEFAULTS["state_owned"],
                "description": "国企占比数据缺失",
                "percentile": None,
                "value": None
            }
        
        # 提取所有国企占比值
        state_owned_values = [s[1] for s in self.state_owned_data]
        
        # 计算分位点
        percentile = self.calculate_percentile(
            school_data.state_owned_ratio, 
            state_owned_values
        )
        
        # 映射到0-100分
        score = percentile
        
        # 生成描述
        for level, info in sorted(SYSTEM_EMPLOYMENT_LEVELS.items(), key=lambda x: x[1]['threshold'], reverse=True):
            if percentile >= info['threshold']:
                description = info['descriptions']['国有企业占比']
                break
        else:
            description = "国企占比数据异常"
        
        return {
            "score": score,
            "description": description,
            "percentile": percentile,
            "value": school_data.state_owned_ratio
        }
    
    def calculate_total_score(self, school_info: SchoolInfo) -> Dict[str, Any]:
        """计算体制内就业评分
        
        Args:
            school_name: 学校名称
            major_code: 专业代码
            
        Returns:
            评分结果
        """
        school_name = school_info.school_name
        major_code = school_info.major_code
        # 计算各维度得分
        civil_servant = self.calculate_civil_servant_score(school_name)
        institution = self.calculate_institution_score(school_name)
        state_owned = self.calculate_state_owned_score(school_name)
        
        # 计算加权总分
        dimension_scores = [
            {
                "name": "公务员占比",
                "score": civil_servant["score"],
                "weight": SYSTEM_EMPLOYMENT_SCORE_WEIGHTS["civil_servant"],
                "weighted_score": civil_servant["score"] * SYSTEM_EMPLOYMENT_SCORE_WEIGHTS["civil_servant"],
                "description": civil_servant["description"],
                "percentile": civil_servant["percentile"],
                "value": civil_servant["value"]
            },
            {
                "name": "事业单位占比",
                "score": institution["score"],
                "weight": SYSTEM_EMPLOYMENT_SCORE_WEIGHTS["institution"],
                "weighted_score": institution["score"] * SYSTEM_EMPLOYMENT_SCORE_WEIGHTS["institution"],
                "description": institution["description"],
                "percentile": institution["percentile"],
                "value": institution["value"]
            },
            {
                "name": "国企占比",
                "score": state_owned["score"],
                "weight": SYSTEM_EMPLOYMENT_SCORE_WEIGHTS["state_owned"],
                "weighted_score": state_owned["score"] * SYSTEM_EMPLOYMENT_SCORE_WEIGHTS["state_owned"],
                "description": state_owned["description"],
                "percentile": state_owned["percentile"],
                "value": state_owned["value"]
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
