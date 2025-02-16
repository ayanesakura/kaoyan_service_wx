import json
import os
from typing import Dict, List
from enum import Enum
from ..beans.input_models import UserInfo, TargetInfo, SchoolInfo
from .constants import (
    SCORE_WEIGHTS, PROBABILITY_LEVELS, MAJOR_MATCH_SCORES,
    COMPETITION_RATIO_SCORES, ENROLLMENT_SIZE_SCORES,
    PREP_TIME_SCORES, ENGLISH_LEVEL_SCORES,
    MAJOR_RANKING_SCORES, SCHOOL_GAP_SCORES,
    GRADE_PREP_MONTHS, EXAM_DAY, MAJOR_DETAIL_FILE,
    COMPETITION_DEFAULT_SCORE
)
import math
from datetime import datetime, date
import calendar

# 在模块级别加载专业数据
def load_major_details() -> Dict:
    """加载专业详细信息"""
    major_details = {}
    try:
        file_path = os.path.join(os.path.dirname(__file__), '..', MAJOR_DETAIL_FILE)
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    major_info = json.loads(line.strip())
                    if '专业名称' in major_info:
                        major_details[major_info['专业名称']] = major_info
                except json.JSONDecodeError:
                    continue
        return major_details
    except Exception as e:
        print(f"Warning: Failed to load major details: {e}")
        return {}

# 全局变量存储专业数据
MAJOR_DETAILS = load_major_details()

class ScoreLevel(Enum):
    """评分等级"""
    IMPOSSIBLE = "不可能"  # <25%
    DIFFICULT = "冲刺"    # 25-45%
    MODERATE = "稳妥"     # 45-75%
    EASY = "保底"         # 75-95%

class DimensionScore:
    """维度得分"""
    def __init__(self, name: str, score: float, weight: float, description: str):
        self.name = name
        self.score = score  # 0-100分
        self.weight = weight  # 权重
        self.description = description
        self.weighted_score = score * weight

class AdmissionScoreCalculator:
    """录取概率评分计算器"""
    
    # 使用constants中定义的权重
    WEIGHTS = {
        "competition": SCORE_WEIGHTS['竞争强度'] / 100,
        "major_match": SCORE_WEIGHTS['专业匹配度'] / 100,
        "school_gap": SCORE_WEIGHTS['学校跨度'] / 100,
        "prep_time": SCORE_WEIGHTS['备考时间'] / 100,
        "english": SCORE_WEIGHTS['英语基础'] / 100,
        "ranking": SCORE_WEIGHTS['专业排名'] / 100,
        "enrollment": SCORE_WEIGHTS['录取规模'] / 100
    }

    def __init__(self, user_info: UserInfo, target_info: TargetInfo):
        self.user_info = user_info
        self.target_info = target_info

    def _get_advance_majors(self, major_name: str) -> List[str]:
        """获取专业的考研方向"""
        major_info = MAJOR_DETAILS.get(major_name, {})
        if not major_info or '考研方向' not in major_info:
            return []
        
        advance_majors = []
        for direction in major_info['考研方向']:
            if direction.get('zymc'):  # 考研专业名称
                advance_majors.append(direction['zymc'])
            if direction.get('advanceMajors'):  # 其他考研方向
                advance_majors.extend(direction['advanceMajors'])
        return advance_majors

    def calculate_prep_time_score(self) -> DimensionScore:
        """计算备考时间得分"""
        current_date = datetime.now()
        grade = self.user_info.grade
        current_year = current_date.year
        
        # 根据年级判断考研年份
        if "大四" in grade or "应届" in grade:
            exam_year = current_year
        elif "大三" in grade:
            exam_year = current_year + 1
        elif "大二" in grade:
            exam_year = current_year + 2
        elif "大一" in grade:
            exam_year = current_year + 3
        else:  # 默认按最近一次考研计算
            exam_year = current_year
        
        # 考研时间固定为12月23日
        exam_date = datetime(exam_year, 12, EXAM_DAY)
        
        # 如果当前日期已经过了今年的考研时间，就算下一年的
        if current_date > exam_date:
            exam_date = datetime(exam_year + 1, 12, EXAM_DAY)
        
        # 计算备考天数
        days_until_exam = (exam_date - current_date).days
        
        # 根据天数确定分数区间
        for (min_days, max_days), score_info in PREP_TIME_SCORES.items():
            if min_days <= days_until_exam < max_days:
                return DimensionScore(
                    "备考时间",
                    score_info['score'],
                    self.WEIGHTS["prep_time"],
                    f"{score_info['desc']}({days_until_exam}天)"
                )
        
        # 如果天数为负或没有匹配的区间，返回最低分
        return DimensionScore(
            "备考时间",
            PREP_TIME_SCORES[(0, 90)]['score'],
            self.WEIGHTS["prep_time"],
            f"备考时间不足({max(0, days_until_exam)}天)"
        )

    def calculate_english_score(self) -> DimensionScore:
        """计算英语基础得分"""
        cet = self.user_info.cet.lower()
        if "六级" in cet:
            score_info = ENGLISH_LEVEL_SCORES['CET6']
        elif "四级" in cet:
            score_info = ENGLISH_LEVEL_SCORES['CET4']
        else:
            score_info = ENGLISH_LEVEL_SCORES['NONE']
        return DimensionScore(
            "英语基础",
            score_info['score'],
            self.WEIGHTS["english"],
            score_info['desc']
        )

    def calculate_major_match_score(self, school_info: SchoolInfo) -> DimensionScore:
        """计算专业匹配度得分"""
        user_major = self.user_info.major
        target_major = school_info.major
        
        # 完全匹配
        if user_major == target_major:
            return DimensionScore(
                "专业匹配度",
                MAJOR_MATCH_SCORES['EXACT'],
                self.WEIGHTS["major_match"],
                "专业完全匹配"
            )
        
        # 获取用户专业的考研方向
        advance_majors = self._get_advance_majors(user_major)
        
        # 检查目标专业是否在考研方向中
        if advance_majors and target_major in advance_majors:
            return DimensionScore(
                "专业匹配度",
                MAJOR_MATCH_SCORES['IN_DIRECTION'],
                self.WEIGHTS["major_match"],
                f"目标专业在考研方向中"
            )
            
        # 不相关专业
        return DimensionScore(
            "专业匹配度",
            MAJOR_MATCH_SCORES['DIFFERENT'],
            self.WEIGHTS["major_match"],
            "跨专业"
        )

    def calculate_competition_score(self, school_info: SchoolInfo) -> DimensionScore:
        """计算竞争强度得分"""
        if not school_info.blb:
            return DimensionScore(
                "竞争强度",
                COMPETITION_DEFAULT_SCORE['score'],
                self.WEIGHTS["competition"],
                COMPETITION_DEFAULT_SCORE['desc']
            )
            
        try:
            latest_blb = school_info.blb[-1]
            # 安全地获取报考人数和录取人数
            bk = float(latest_blb.get('bk', 0))
            lq = float(latest_blb.get('lq', 1))  # 默认值为1避免除以0
            
            ratio = bk / lq if lq > 0 else 10
            
            for (min_ratio, max_ratio), score_info in COMPETITION_RATIO_SCORES.items():
                if min_ratio <= ratio < max_ratio:
                    return DimensionScore(
                        "竞争强度",
                        score_info['score'],
                        self.WEIGHTS["competition"],
                        f"{score_info['desc']}(报录比 {ratio:.1f}:1)"
                    )
                    
            # 如果没有匹配的区间，返回默认值
            return DimensionScore(
                "竞争强度",
                COMPETITION_DEFAULT_SCORE['score'],
                self.WEIGHTS["competition"],
                COMPETITION_DEFAULT_SCORE['desc']
            )
        except Exception as e:
            logger.error(f"计算竞争强度得分时出错: {str(e)}")
            return DimensionScore(
                "竞争强度",
                COMPETITION_DEFAULT_SCORE['score'],
                self.WEIGHTS["competition"],
                COMPETITION_DEFAULT_SCORE['desc']
            )

    def calculate_school_gap_score(self, school_info: SchoolInfo) -> DimensionScore:
        """计算学校档次跨度得分"""
        def get_school_level(school: SchoolInfo) -> int:
            if school.is_985 == "1":
                return 3
            elif school.is_211 == "1":
                return 2
            return 1
            
        target_level = get_school_level(school_info)
        user_level = 1  # 假设用户学校档次为1
        
        gap = target_level - user_level
        score_info = SCHOOL_GAP_SCORES[gap]
            
        return DimensionScore(
            "学校跨度",
            score_info['score'],
            self.WEIGHTS["school_gap"],
            score_info['desc']
        )

    def calculate_ranking_score(self) -> DimensionScore:
        """计算专业排名得分"""
        rank = self.user_info.rank
        if "前10%" in rank:
            score_info = MAJOR_RANKING_SCORES['TOP10']
        elif "前20%" in rank:
            score_info = MAJOR_RANKING_SCORES['TOP20']
        elif "前50%" in rank:
            score_info = MAJOR_RANKING_SCORES['TOP50']
        else:
            score_info = MAJOR_RANKING_SCORES['OTHER']
            
        return DimensionScore(
            "专业排名",
            score_info['score'],
            self.WEIGHTS["ranking"],
            score_info['desc']
        )

    def calculate_enrollment_score(self, school_info: SchoolInfo) -> DimensionScore:
        """计算录取规模得分"""
        total_enrollment = 0
        for direction in school_info.directions:
            try:
                num = int(''.join(filter(str.isdigit, direction.zsrs)))
                total_enrollment += num
            except:
                continue
                
        for (min_size, max_size), score_info in ENROLLMENT_SIZE_SCORES.items():
            if min_size <= total_enrollment < max_size:
                return DimensionScore(
                    "录取规模",
                    score_info['score'],
                    self.WEIGHTS["enrollment"],
                    f"{score_info['desc']}({total_enrollment}人)"
                )

    def calculate_probability(self, total_score: float) -> float:
        """将总分转换为概率"""
        return 1 / (1 + math.exp(-0.02 * (total_score - 60))) * 100

    def get_score_level(self, probability: float) -> ScoreLevel:
        """根据概率确定评分等级"""
        if probability < PROBABILITY_LEVELS['IMPOSSIBLE']:
            return ScoreLevel.IMPOSSIBLE
        elif probability < PROBABILITY_LEVELS['DIFFICULT']:
            return ScoreLevel.DIFFICULT
        elif probability < PROBABILITY_LEVELS['MODERATE']:
            return ScoreLevel.MODERATE
        else:
            return ScoreLevel.EASY

    def calculate(self, school_info: SchoolInfo) -> Dict:
        """计算总评分和录取概率"""
        # 计算各维度得分
        dimension_scores = [
            self.calculate_prep_time_score(),
            self.calculate_english_score(),
            self.calculate_major_match_score(school_info),
            self.calculate_competition_score(school_info),
            self.calculate_school_gap_score(school_info),
            self.calculate_ranking_score(),
            self.calculate_enrollment_score(school_info)
        ]
        
        # 计算总分
        total_score = sum(score.weighted_score for score in dimension_scores)
        
        # 计算概率
        probability = self.calculate_probability(total_score)
        
        # 确定等级
        level = self.get_score_level(probability)
        
        return {
            "school_name": school_info.school_name,
            "total_score": round(total_score, 2),
            "probability": round(probability, 2),
            "level": level.value,
            "dimension_scores": [
                {
                    "name": score.name,
                    "score": round(score.score, 2),
                    "weight": score.weight,
                    "weighted_score": round(score.weighted_score, 2),
                    "description": score.description
                }
                for score in dimension_scores
            ]
        } 