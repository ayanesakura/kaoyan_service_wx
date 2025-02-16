import json
import os
from typing import Dict, List, Any
from loguru import logger
from wxcloudrun.beans.input_models import UserInfo, TargetInfo, SchoolInfo
from wxcloudrun.score_card.constants import (
    LOCATION_SCORE_WEIGHTS, 
    LOCATION_SCORE_DEFAULTS,
    CITY_SCORES,
    HOMETOWN_MATCH_SCORES,
    WORK_CITY_MATCH_SCORES
)

class LocationScoreCalculator:
    """地理位置评分计算器"""
    
    def __init__(self, user_info: UserInfo, target_info: TargetInfo):
        self.user_info = user_info
        self.target_info = target_info
        
    def calculate_living_cost_score(self, school_info: SchoolInfo) -> float:
        """
        计算生活成本得分
        :param school_info: 学校信息
        :return: 0-100分，分数越高表示生活成本越低
        """
        city = school_info.city
        
        if not CITY_SCORES or city not in CITY_SCORES:
            logger.warning(f"城市 {city} 未找到生活成本数据，使用默认分数")
            return LOCATION_SCORE_DEFAULTS['生活成本']
            
        try:
            score = CITY_SCORES[city]['分位点得分']['性价比得分']
            if score <= 0:
                logger.warning(f"城市 {city} 性价比得分为0，使用默认分数")
                return LOCATION_SCORE_DEFAULTS['生活成本']
            return score
        except Exception as e:
            logger.error(f"计算城市 {city} 生活成本得分时出错: {str(e)}")
            return LOCATION_SCORE_DEFAULTS['生活成本']
        
    def calculate_hometown_match_score(self, school_info: SchoolInfo) -> float:
        """
        计算家乡匹配度得分
        :param school_info: 学校信息
        :return: 0-100分，分数越高表示与家乡越近
        """
        if not self.user_info.hometown:
            logger.warning("未填写家乡信息，使用默认分数")
            return LOCATION_SCORE_DEFAULTS['家乡匹配度']
            
        try:
            school_city = school_info.city
            school_province = school_info.province
            hometown = self.user_info.hometown
            
            if hometown.city == school_city:
                logger.debug(f"城市匹配（{hometown.city}），返回最高分")
                return HOMETOWN_MATCH_SCORES['SAME_CITY']
                
            if hometown.province == school_province:
                logger.debug(f"省份匹配（{hometown.province}），返回中等分数")
                return HOMETOWN_MATCH_SCORES['SAME_PROVINCE']
                
            logger.debug(f"不同省份（{hometown.province} vs {school_province}），返回基础分数")
            return HOMETOWN_MATCH_SCORES['DIFFERENT']
            
        except Exception as e:
            logger.error(f"计算家乡匹配度时出错: {str(e)}")
            return LOCATION_SCORE_DEFAULTS['家乡匹配度']
        
    def calculate_education_resource_score(self, school_info: SchoolInfo) -> float:
        """
        计算教育资源得分
        :param school_info: 学校信息
        :return: 0-100分，分数越高表示教育资源越丰富
        """
        city = school_info.city
        
        if not CITY_SCORES or city not in CITY_SCORES:
            return LOCATION_SCORE_DEFAULTS['教育资源']
            
        try:
            score = CITY_SCORES[city]['分位点得分']['本科院校得分']
            return score if score > 0 else LOCATION_SCORE_DEFAULTS['教育资源']
        except:
            return LOCATION_SCORE_DEFAULTS['教育资源']
        
    def calculate_medical_resource_score(self, school_info: SchoolInfo) -> float:
        """
        计算医疗资源得分
        :param school_info: 学校信息
        :return: 0-100分，分数越高表示医疗资源越丰富
        """
        city = school_info.city
        
        if not CITY_SCORES or city not in CITY_SCORES:
            return LOCATION_SCORE_DEFAULTS['医疗资源']
            
        try:
            score = CITY_SCORES[city]['分位点得分']['三甲医院得分']
            return score if score > 0 else LOCATION_SCORE_DEFAULTS['医疗资源']
        except:
            return LOCATION_SCORE_DEFAULTS['医疗资源']
        
    def calculate_work_city_match_score(self, school_info: SchoolInfo) -> float:
        """
        计算意向工作城市匹配度得分
        :param school_info: 学校信息
        :return: 0-100分，分数越高表示越符合意向工作城市
        """
        # 如果没有设置意向工作城市，返回默认分数
        if not self.target_info.work_cities:
            logger.warning("未设置意向工作城市，使用默认分数")
            return LOCATION_SCORE_DEFAULTS['工作城市匹配度']
            
        try:
            school_city = school_info.city
            school_province = school_info.province
            
            # 检查城市匹配
            for work_city in self.target_info.work_cities:
                if work_city.city == school_city:
                    logger.debug(f"城市匹配（{school_city}），返回最高分")
                    return WORK_CITY_MATCH_SCORES['CITY_MATCH']
            
            # 检查省份匹配
            for work_city in self.target_info.work_cities:
                if work_city.province == school_province:
                    logger.debug(f"省份匹配（{school_province}），返回中等分数")
                    return WORK_CITY_MATCH_SCORES['PROVINCE_MATCH']
            
            # 无匹配
            logger.debug(f"学校所在地（{school_province}{school_city}）与意向工作城市无匹配")
            return WORK_CITY_MATCH_SCORES['NO_MATCH']
            
        except Exception as e:
            logger.error(f"计算工作城市匹配度时出错: {str(e)}")
            return LOCATION_SCORE_DEFAULTS['工作城市匹配度']
        
    def calculate_total_score(self, school_info: SchoolInfo) -> Dict[str, Any]:
        """
        计算总分
        :param school_info: 学校信息
        :return: 包含各维度分数和总分的字典，各维度分数0-100分，总分为加权后的0-100分
        """
        scores = {
            "生活成本": self.calculate_living_cost_score(school_info),
            "家乡匹配度": self.calculate_hometown_match_score(school_info),
            "教育资源": self.calculate_education_resource_score(school_info),
            "医疗资源": self.calculate_medical_resource_score(school_info),
            "工作城市匹配度": self.calculate_work_city_match_score(school_info)
        }
        
        # 计算加权总分
        total_score = sum(
            score * LOCATION_SCORE_WEIGHTS[dimension]
            for dimension, score in scores.items()
        )
        
        return {
            "总分": total_score,
            "scores": scores,
            "details": {
                "生活成本": {"score": scores["生活成本"]},
                "家乡匹配度": {"score": scores["家乡匹配度"]},
                "教育资源": {"score": scores["教育资源"]},
                "医疗资源": {"score": scores["医疗资源"]},
                "工作城市匹配度": {"score": scores["工作城市匹配度"]}
            }
        } 