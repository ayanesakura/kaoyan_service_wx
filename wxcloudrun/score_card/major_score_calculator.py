from typing import Dict, List, Tuple, Any
from loguru import logger
from wxcloudrun.beans.input_models import UserInfo, TargetInfo, SchoolInfo
from wxcloudrun.score_card.constants import (
    MAJOR_SCORE_WEIGHTS,
    MAJOR_SCORE_DEFAULTS,
    SCHOOL_REPUTATION_SCORES,
    XUEKE_LEVEL_SCORES,
    SATISFACTION_SCORE_RANGES
)
from wxcloudrun.score_card.school_data_loader import SCHOOL_DATA

class MajorScoreCalculator:
    """学校专业评分计算器"""
    
    def __init__(self, user_info: UserInfo, target_info: TargetInfo):
        self.user_info = user_info
        self.target_info = target_info
        
    def _get_school_data(self, school_info: SchoolInfo) -> Dict[str, Any]:
        """获取学校专业数据"""
        key = f"{school_info.school_name}-{school_info.major}"
        return SCHOOL_DATA.get(key, {})
        
    def _get_satisfaction_score(self, satisfaction: float) -> float:
        """根据满意度值获取对应分数"""
        if not satisfaction:
            return MAJOR_SCORE_DEFAULTS['学校综合满意度']
            
        for (min_val, max_val), score in SATISFACTION_SCORE_RANGES.items():
            if min_val <= satisfaction <= max_val:
                return score
        return MAJOR_SCORE_DEFAULTS['学校综合满意度']
        
    def calculate_school_reputation_score(self, school_info: SchoolInfo) -> float:
        """
        计算学校知名度得分
        :param school_info: 学校信息
        :return: 0-100分，分数越高表示知名度越高
        """
        try:
            school_data = self._get_school_data(school_info)
            
            # 如果没有获取到学校数据，返回未知等级分数
            if not school_data:
                logger.warning(f"学校 {school_info.school_name} 未找到等级数据，按未知等级处理")
                return SCHOOL_REPUTATION_SCORES['UNKNOWN']
            
            if school_data.get('is_c9') == '是':
                logger.debug(f"学校 {school_info.school_name} 是C9高校")
                return SCHOOL_REPUTATION_SCORES['C9']
            elif school_data.get('is_985') == '是':
                logger.debug(f"学校 {school_info.school_name} 是985高校")
                return SCHOOL_REPUTATION_SCORES['985']
            elif school_data.get('is_211') == '是':
                logger.debug(f"学校 {school_info.school_name} 是211高校")
                return SCHOOL_REPUTATION_SCORES['211']
            elif school_data.get('is_first_tier') == '是':
                logger.debug(f"学校 {school_info.school_name} 是双一流高校")
                return SCHOOL_REPUTATION_SCORES['双一流']
            else:
                logger.debug(f"学校 {school_info.school_name} 是其他层次高校")
                return SCHOOL_REPUTATION_SCORES['OTHER']
        except Exception as e:
            logger.error(f"计算学校知名度得分时出错: {str(e)}")
            return SCHOOL_REPUTATION_SCORES['UNKNOWN']
            
    def calculate_major_rank_score(self, school_info: SchoolInfo) -> float:
        """
        计算专业排名得分
        :param school_info: 学校信息
        :return: 0-100分，分数越高表示排名越靠前
        """
        try:
            school_data = self._get_school_data(school_info)
            
            # 如果没有获取到学校数据，返回未知等级分数
            if not school_data:
                logger.warning(f"专业 {school_info.major} 未找到数据，按未知等级处理")
                return XUEKE_LEVEL_SCORES['UNKNOWN']
            
            xueke_level = school_data.get('xueke_level')
            if not xueke_level:
                logger.warning(f"专业 {school_info.major} 未找到学科评级数据，按未知等级处理")
                return XUEKE_LEVEL_SCORES['UNKNOWN']
            
            score = XUEKE_LEVEL_SCORES.get(xueke_level, XUEKE_LEVEL_SCORES['OTHER'])
            logger.debug(f"专业 {school_info.major} 学科评级为 {xueke_level}，得分 {score}")
            return score
        except Exception as e:
            logger.error(f"计算专业排名得分时出错: {str(e)}")
            return XUEKE_LEVEL_SCORES['UNKNOWN']
            
    def calculate_school_satisfaction_score(self, school_info: SchoolInfo) -> float:
        """
        计算学校综合满意度得分
        :param school_info: 学校信息
        :return: 0-100分，分数越高表示满意度越高
        """
        try:
            school_data = self._get_school_data(school_info)
            satisfaction = school_data.get('school_overall_satisfaction')
            
            if not satisfaction:
                logger.warning(f"学校 {school_info.school_name} 未找到满意度数据")
                return MAJOR_SCORE_DEFAULTS['学校综合满意度']
                
            score = self._get_satisfaction_score(satisfaction)
            logger.debug(f"学校 {school_info.school_name} 满意度为 {satisfaction}，得分 {score}")
            return score
        except Exception as e:
            logger.error(f"计算学校满意度得分时出错: {str(e)}")
            return MAJOR_SCORE_DEFAULTS['学校综合满意度']
            
    def calculate_major_satisfaction_score(self, school_info: SchoolInfo) -> float:
        """
        计算专业综合满意度得分
        :param school_info: 学校信息
        :return: 0-100分，分数越高表示满意度越高
        """
        try:
            school_data = self._get_school_data(school_info)
            satisfaction = school_data.get('major_satisfaction_overall')
            
            if not satisfaction:
                logger.warning(f"专业 {school_info.major} 未找到满意度数据")
                return MAJOR_SCORE_DEFAULTS['专业综合满意度']
                
            score = self._get_satisfaction_score(satisfaction)
            logger.debug(f"专业 {school_info.major} 满意度为 {satisfaction}，得分 {score}")
            return score
        except Exception as e:
            logger.error(f"计算专业满意度得分时出错: {str(e)}")
            return MAJOR_SCORE_DEFAULTS['专业综合满意度']
        
    def calculate_total_score(self, school_info: SchoolInfo) -> Dict[str, float]:
        """
        计算总分
        :param school_info: 学校信息
        :return: 包含各维度分数和总分的字典，各维度分数0-100分，总分为加权后的0-100分
        """
        scores = {
            "学校知名度": self.calculate_school_reputation_score(school_info),
            "专业排名": self.calculate_major_rank_score(school_info),
            "学校综合满意度": self.calculate_school_satisfaction_score(school_info),
            "专业综合满意度": self.calculate_major_satisfaction_score(school_info)
        }
        
        # 计算加权总分
        total_score = sum(
            score * MAJOR_SCORE_WEIGHTS[dimension]
            for dimension, score in scores.items()
        )
        
        scores["总分"] = total_score
        return scores 