from typing import Dict, List, Tuple, Any
from loguru import logger
from wxcloudrun.beans.input_models import UserInfo, TargetInfo, SchoolInfo
from wxcloudrun.score_card.constants import (
    MAJOR_SCORE_WEIGHTS,
    MAJOR_SCORE_DEFAULTS,
    SCHOOL_REPUTATION_SCORES,
    XUEKE_LEVEL_SCORES,
    SATISFACTION_SCORE_RANGES,
    SCORE_LEVELS
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
        
    def calculate_school_reputation_score(self, school_info: SchoolInfo) -> Dict:
        """计算学校知名度得分"""
        try:
            school_data = self._get_school_data(school_info)
            
            # 如果没有获取到学校数据，返回未知等级分数
            if not school_data:
                logger.warning(f"学校 {school_info.school_name} 未找到等级数据，按未知等级处理")
                return {
                    'score': SCHOOL_REPUTATION_SCORES['UNKNOWN'],
                    'source': 'default'
                }
            
            if school_data.get('is_c9') == '是':
                logger.debug(f"学校 {school_info.school_name} 是C9高校")
                return {
                    'score': SCHOOL_REPUTATION_SCORES['C9'],
                    'source': 'real'
                }
            elif school_data.get('is_985') == '是':
                logger.debug(f"学校 {school_info.school_name} 是985高校")
                return {
                    'score': SCHOOL_REPUTATION_SCORES['985'],
                    'source': 'real'
                }
            elif school_data.get('is_211') == '是':
                logger.debug(f"学校 {school_info.school_name} 是211高校")
                return {
                    'score': SCHOOL_REPUTATION_SCORES['211'],
                    'source': 'real'
                }
            elif school_data.get('is_first_tier') == '是':
                logger.debug(f"学校 {school_info.school_name} 是双一流高校")
                return {
                    'score': SCHOOL_REPUTATION_SCORES['双一流'],
                    'source': 'real'
                }
            else:
                logger.debug(f"学校 {school_info.school_name} 是其他层次高校")
                return {
                    'score': SCHOOL_REPUTATION_SCORES['OTHER'],
                    'source': 'real'
                }
        except Exception as e:
            logger.error(f"计算学校知名度得分时出错: {str(e)}")
            return {
                'score': SCHOOL_REPUTATION_SCORES['UNKNOWN'],
                'source': 'default'
            }
            
    def calculate_major_rank_score(self, school_info: SchoolInfo) -> Dict:
        """计算专业排名得分"""
        try:
            school_data = self._get_school_data(school_info)
            rank = school_data.get('major_rank')
            
            if not rank:
                logger.warning(f"专业 {school_info.major} 未找到排名数据")
                return {
                    'score': MAJOR_SCORE_DEFAULTS['专业排名'],
                    'source': 'default'
                }
            
            return {
                'score': rank,
                'source': 'real'
            }
        except Exception as e:
            logger.error(f"计算专业排名得分时出错: {str(e)}")
            return {
                'score': MAJOR_SCORE_DEFAULTS['专业排名'],
                'source': 'default'
            }
            
    def calculate_school_satisfaction_score(self, school_info: SchoolInfo) -> Dict:
        """计算学校综合满意度得分"""
        try:
            school_data = self._get_school_data(school_info)
            satisfaction = school_data.get('school_satisfaction_overall')
            
            if not satisfaction:
                logger.warning(f"学校 {school_info.school_name} 未找到满意度数据")
                return {
                    'score': MAJOR_SCORE_DEFAULTS['学校综合满意度'],
                    'source': 'default'
                }
            
            score = self._get_satisfaction_score(satisfaction)
            logger.debug(f"学校 {school_info.school_name} 满意度为 {satisfaction}，得分 {score}")
            return {
                'score': score,
                'source': 'real'
            }
        except Exception as e:
            logger.error(f"计算学校满意度得分时出错: {str(e)}")
            return {
                'score': MAJOR_SCORE_DEFAULTS['学校综合满意度'],
                'source': 'default'
            }
            
    def calculate_major_satisfaction_score(self, school_info: SchoolInfo) -> Dict:
        """计算专业综合满意度得分"""
        try:
            school_data = self._get_school_data(school_info)
            satisfaction = school_data.get('major_satisfaction_overall')
            
            if not satisfaction:
                logger.warning(f"专业 {school_info.major} 未找到满意度数据")
                return {
                    'score': MAJOR_SCORE_DEFAULTS['专业综合满意度'],
                    'source': 'default'
                }
            
            score = self._get_satisfaction_score(satisfaction)
            logger.debug(f"专业 {school_info.major} 满意度为 {satisfaction}，得分 {score}")
            return {
                'score': score,
                'source': 'real'
            }
        except Exception as e:
            logger.error(f"计算专业满意度得分时出错: {str(e)}")
            return {
                'score': MAJOR_SCORE_DEFAULTS['专业综合满意度'],
                'source': 'default'
            }
        
    def _get_description(self, dimension: str, score: float) -> str:
        """获取维度描述"""
        if score >= SCORE_LEVELS['high']['threshold']:
            return SCORE_LEVELS['high']['descriptions'][dimension]
        elif score >= SCORE_LEVELS['medium']['threshold']:
            return SCORE_LEVELS['medium']['descriptions'][dimension]
        return SCORE_LEVELS['low']['descriptions'][dimension]

    def calculate_total_score(self, school_info: SchoolInfo) -> Dict[str, Any]:
        """计算总分"""
        # 方法名映射
        method_map = {
            '学校知名度': 'calculate_school_reputation_score',
            '专业排名': 'calculate_major_rank_score',
            '学校综合满意度': 'calculate_school_satisfaction_score',
            '专业综合满意度': 'calculate_major_satisfaction_score'
        }
        
        # 计算各维度得分
        dimension_scores = []
        for dimension in MAJOR_SCORE_WEIGHTS.keys():
            score_info = getattr(self, method_map[dimension])(school_info)
            dimension_scores.append({
                "name": dimension,
                "score": score_info['score'],
                "source": score_info['source'],
                "weight": MAJOR_SCORE_WEIGHTS[dimension],
                "description": self._get_description(dimension, score_info['score']),
                "weighted_score": score_info['score'] * MAJOR_SCORE_WEIGHTS[dimension]
            })
        
        # 计算总分
        total_score = sum(score["weighted_score"] for score in dimension_scores)
        
        return {
            "dimension_scores": dimension_scores,
            "total_score": total_score,
            "school_name": school_info.school_name
        } 