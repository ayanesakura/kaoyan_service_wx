from typing import Dict, List
from wxcloudrun.beans.input_models import UserInfo, SchoolInfo
import math

class AdmissionScoreCalculator:
    """录取评分计算器"""
    
    def __init__(self, user_info: UserInfo):
        self.user_info = user_info
        
    def calculate_preparation_time_score(self, grade: str) -> float:
        """计算备考时间得分"""
        # ... 原有的备考时间计算逻辑
        pass
        
    def calculate_english_score(self, cet: str) -> float:
        """计算英语基础得分"""
        if "六级" in cet:
            return 5
        elif "四级" in cet:
            return 2
        return 0
        
    def calculate_major_match_score(self, school_info: SchoolInfo) -> float:
        """计算专业匹配度得分"""
        # ... 原有的专业匹配度计算逻辑
        pass
        
    def calculate_competition_score(self, school_info: SchoolInfo) -> float:
        """计算竞争强度得分"""
        # ... 原有的竞争强度计算逻辑
        pass
        
    def calculate_enrollment_score(self, school_info: SchoolInfo) -> float:
        """计算录取规模得分"""
        # ... 原有的录取规模计算逻辑
        pass
        
    def calculate_school_level_score(self, school_info: SchoolInfo) -> float:
        """计算学校跨度得分"""
        # ... 原有的学校跨度计算逻辑
        pass
        
    def calculate_major_rank_score(self) -> float:
        """计算专业排名得分"""
        # ... 原有的专业排名计算逻辑
        pass
        
    def calculate_total_score(self, school_info: SchoolInfo) -> Dict[str, float]:
        """计算总分"""
        scores = {
            "备考时间": self.calculate_preparation_time_score(self.user_info.grade),
            "英语基础": self.calculate_english_score(self.user_info.cet),
            "专业匹配度": self.calculate_major_match_score(school_info),
            "竞争强度": self.calculate_competition_score(school_info),
            "录取规模": self.calculate_enrollment_score(school_info),
            "学校跨度": self.calculate_school_level_score(school_info),
            "专业排名": self.calculate_major_rank_score()
        }
        
        scores["总分"] = sum(scores.values())
        return scores

def calculate_admission_probability(score: float) -> float:
    """
    计算录取概率
    使用 Logistic 函数: P = 1 / (1 + e^(-0.1 * (S - 65)))
    """
    try:
        return 1 / (1 + math.exp(-0.1 * (score - 65)))
    except:
        return 0 