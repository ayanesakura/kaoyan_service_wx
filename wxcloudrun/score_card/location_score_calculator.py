import json
import os
from typing import Dict, List, Any
from loguru import logger
from wxcloudrun.beans.input_models import UserInfo, TargetInfo, SchoolInfo, Area
from wxcloudrun.score_card.constants import (
    LOCATION_SCORE_WEIGHTS, 
    LOCATION_SCORE_DEFAULTS,
    CITY_SCORES,
    HOMETOWN_MATCH_SCORES,
    WORK_CITY_MATCH_SCORES
)
# from wxcloudrun.score_card.city_data_loader import CITY_SCORES  # 修改导入

class LocationScoreCalculator:
    """地理位置评分计算器"""
    
    def __init__(self, user_info: UserInfo, target_info: TargetInfo):
        self.user_info = user_info
        self.target_info = target_info
        
    def calculate_living_cost_score(self, city: str) -> Dict:
        """计算生活成本得分"""
        try:
            city_data = CITY_SCORES.get(city)
            if city_data:
                score = city_data['分位点得分']['性价比得分']
                source = 'real'
            else:
                score = LOCATION_SCORE_DEFAULTS['生活成本']
                source = 'default'
                logger.warning(f"未找到城市 {city} 的生活成本数据，使用默认值")
            
            return {
                'score': score,
                'source': source
            }
        except Exception as e:
            logger.error(f"计算生活成本得分时出错: {str(e)}")
            return {
                'score': LOCATION_SCORE_DEFAULTS['生活成本'],
                'source': 'default'
            }
        
    def calculate_hometown_match_score(self, school_info: SchoolInfo) -> Dict:
        """计算家乡匹配度得分"""
        if not self.user_info.hometown:
            logger.warning("未填写家乡信息，使用默认分数")
            return {
                'score': LOCATION_SCORE_DEFAULTS['家乡匹配度'],
                'source': 'default'
            }
            
        try:
            school_city = school_info.city
            school_province = school_info.province
            hometown = self.user_info.hometown
            
            if hometown.city == school_city:
                return {
                    'score': HOMETOWN_MATCH_SCORES['SAME_CITY'],
                    'source': 'calculated'
                }
                
            if hometown.province == school_province:
                return {
                    'score': HOMETOWN_MATCH_SCORES['SAME_PROVINCE'],
                    'source': 'calculated'
                }
                
            return {
                'score': HOMETOWN_MATCH_SCORES['DIFFERENT'],
                'source': 'calculated'
            }
            
        except Exception as e:
            logger.error(f"计算家乡匹配度时出错: {str(e)}")
            return {
                'score': LOCATION_SCORE_DEFAULTS['家乡匹配度'],
                'source': 'default'
            }
        
    def calculate_education_resource_score(self, city: str) -> Dict:
        """计算教育资源得分"""
        try:
            city_data = CITY_SCORES.get(city)
            if city_data:
                score = city_data['分位点得分']['本科院校得分']
                source = 'real'
            else:
                score = LOCATION_SCORE_DEFAULTS['教育资源']
                source = 'default'
                logger.warning(f"未找到城市 {city} 的教育资源数据，使用默认值")
            
            return {
                'score': score,
                'source': source
            }
        except Exception as e:
            logger.error(f"计算教育资源得分时出错: {str(e)}")
            return {
                'score': LOCATION_SCORE_DEFAULTS['教育资源'],
                'source': 'default'
            }
        
    def calculate_medical_resource_score(self, city: str) -> Dict:
        """计算医疗资源得分"""
        try:
            city_data = CITY_SCORES.get(city)
            if city_data:
                score = city_data['分位点得分']['三甲医院得分']
                source = 'real'
            else:
                score = LOCATION_SCORE_DEFAULTS['医疗资源']
                source = 'default'
                logger.warning(f"未找到城市 {city} 的医疗资源数据，使用默认值")
            
            return {
                'score': score,
                'source': source
            }
        except Exception as e:
            logger.error(f"计算医疗资源得分时出错: {str(e)}")
            return {
                'score': LOCATION_SCORE_DEFAULTS['医疗资源'],
                'source': 'default'
            }
        
    def calculate_work_city_match_score(self, school_info: SchoolInfo) -> Dict:
        """计算意向工作城市匹配度得分"""
        if not self.target_info.work_cities:
            logger.warning("未设置意向工作城市，使用默认分数")
            return {
                'score': LOCATION_SCORE_DEFAULTS['工作城市匹配度'],
                'source': 'default'
            }
            
        try:
            school_city = school_info.city
            school_province = school_info.province
            
            for work_city in self.target_info.work_cities:
                if work_city.city == school_city:
                    return {
                        'score': WORK_CITY_MATCH_SCORES['CITY_MATCH'],
                        'source': 'calculated'
                    }
            
            for work_city in self.target_info.work_cities:
                if work_city.province == school_province:
                    return {
                        'score': WORK_CITY_MATCH_SCORES['PROVINCE_MATCH'],
                        'source': 'calculated'
                    }
            
            return {
                'score': WORK_CITY_MATCH_SCORES['NO_MATCH'],
                'source': 'calculated'
            }
            
        except Exception as e:
            logger.error(f"计算工作城市匹配度时出错: {str(e)}")
            return {
                'score': LOCATION_SCORE_DEFAULTS['工作城市匹配度'],
                'source': 'default'
            }
        
    def calculate_total_score(self, school_info: SchoolInfo) -> Dict[str, Any]:
        """计算地理位置评分
        
        Args:
            school_info: 学校信息
            
        Returns:
            评分结果
        """
        # 检查CITY_SCORES是否有数据
        logger.debug(f"计算 {school_info.school_name} 的地理位置得分")
        logger.debug(f"城市评分数据: {CITY_SCORES.get(school_info.city)}")
        
        # 计算各维度得分
        living_cost = self.calculate_living_cost_score(school_info.city)
        education = self.calculate_education_resource_score(school_info.city)
        medical = self.calculate_medical_resource_score(school_info.city)
        hometown = self.calculate_hometown_match_score(school_info)
        work_city = self.calculate_work_city_match_score(school_info)
        
        dimension_scores = [
            {
                "name": "生活成本",
                "score": living_cost['score'],
                "source": living_cost['source'],
                "weight": LOCATION_SCORE_WEIGHTS["生活成本"],
                "description": self._get_living_cost_description(living_cost['score']),
                "weighted_score": living_cost['score'] * LOCATION_SCORE_WEIGHTS["生活成本"]
            },
            {
                "name": "家乡匹配度",
                "score": hometown['score'],
                "source": hometown['source'],
                "weight": LOCATION_SCORE_WEIGHTS["家乡匹配度"],
                "description": self._get_hometown_match_description(school_info),
                "weighted_score": hometown['score'] * LOCATION_SCORE_WEIGHTS["家乡匹配度"]
            },
            {
                "name": "教育资源",
                "score": education['score'],
                "source": education['source'],
                "weight": LOCATION_SCORE_WEIGHTS["教育资源"],
                "description": self._get_education_resource_description(education['score']),
                "weighted_score": education['score'] * LOCATION_SCORE_WEIGHTS["教育资源"]
            },
            {
                "name": "医疗资源",
                "score": medical['score'],
                "source": medical['source'],
                "weight": LOCATION_SCORE_WEIGHTS["医疗资源"],
                "description": self._get_medical_resource_description(medical['score']),
                "weighted_score": medical['score'] * LOCATION_SCORE_WEIGHTS["医疗资源"]
            },
            {
                "name": "工作城市匹配度",
                "score": work_city['score'],
                "source": work_city['source'],
                "weight": LOCATION_SCORE_WEIGHTS["工作城市匹配度"],
                "description": self._get_work_city_match_description(school_info),
                "weighted_score": work_city['score'] * LOCATION_SCORE_WEIGHTS["工作城市匹配度"]
            }
        ]
        
        # 计算总分
        total_score = sum(score["weighted_score"] for score in dimension_scores)
        
        return {
            "dimension_scores": dimension_scores,
            "total_score": total_score,
            "school_name": school_info.school_name
        }

    def _get_living_cost_description(self, score: float) -> str:
        """获取生活成本描述"""
        if score >= 80:
            return "生活成本较低"
        elif score >= 60:
            return "生活成本适中"
        else:
            return "生活成本较高"

    def _get_hometown_match_description(self, school_info: SchoolInfo) -> str:
        """获取家乡匹配度描述"""
        if not self.user_info.hometown:
            return "未提供家乡信息"
        if self.user_info.hometown.city == school_info.city:
            return "与家乡在同一城市"
        elif self.user_info.hometown.province == school_info.province:
            return "与家乡在同一省份"
        return "与家乡跨省"

    def _get_education_resource_description(self, score: float) -> str:
        """获取教育资源描述"""
        if score >= 80:
            return "教育资源丰富"
        elif score >= 60:
            return "教育资源一般"
        else:
            return "教育资源较少"

    def _get_medical_resource_description(self, score: float) -> str:
        """获取医疗资源描述"""
        if score >= 80:
            return "医疗资源丰富"
        elif score >= 60:
            return "医疗资源一般"
        else:
            return "医疗资源较少"

    def _get_work_city_match_description(self, school_info: SchoolInfo) -> str:
        """获取工作城市匹配度描述"""
        if not self.target_info.work_cities:
            return "未设置意向工作城市"
        for work_city in self.target_info.work_cities:
            if work_city.city == school_info.city:
                return "与意向工作城市完全匹配"
            elif work_city.province == school_info.province:
                return "与意向工作城市在同一省份"
        return "与意向工作城市不匹配" 