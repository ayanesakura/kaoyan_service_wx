import json
import os
from typing import Dict, List, Any
from enum import Enum
from ..beans.input_models import UserInfo, TargetInfo, SchoolInfo, Area
from .constants import (
    SCORE_WEIGHTS, PROBABILITY_LEVELS, MAJOR_MATCH_SCORES,
    COMPETITION_RATIO_SCORES, ENROLLMENT_SIZE_SCORES,
    PREP_TIME_SCORES, ENGLISH_LEVEL_SCORES,
    MAJOR_RANKING_SCORES, SCHOOL_GAP_SCORES,
    GRADE_PREP_MONTHS, EXAM_DAY, MAJOR_DETAIL_FILE,
    COMPETITION_DEFAULT_SCORE,
    ADMISSION_SCORE_WEIGHTS,
    ADMISSION_SCORE_DEFAULTS,
    SCHOOL_REPUTATION_WEIGHT,
    MAJOR_REPUTATION_WEIGHT,
    EXAM_MONTH
)
from wxcloudrun.score_card.score_data_loader import (
    get_school_data,
    get_major_data,
    SCHOOL_DATA,
    MAJOR_DATA
)
import math
from datetime import datetime, date
import calendar
from loguru import logger

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

# 学校知名度评分 - 增加区分度
SCHOOL_REPUTATION_SCORES = {
    (1, 2): {'score': 30, 'desc': '世界顶尖名校，竞争极其激烈'},
    (3, 5): {'score': 40, 'desc': '顶尖名校，竞争极其激烈'},
    (6, 10): {'score': 50, 'desc': '超一流名校，竞争非常激烈'},
    (11, 20): {'score': 60, 'desc': '一流名校，竞争激烈'},
    (21, 50): {'score': 70, 'desc': '知名高校，竞争较激烈'},
    (51, 100): {'score': 80, 'desc': '较知名高校，竞争适中'},
    (101, 200): {'score': 85, 'desc': '普通高校，竞争较低'},
    (201, 500): {'score': 90, 'desc': '一般高校，竞争低'},
    (501, 1000): {'score': 95, 'desc': '普通院校，竞争很低'}
}

# 专业知名度评分 - 调整为实际存在的学科评估等级
MAJOR_REPUTATION_SCORES = {
    'A+': {'score': 40, 'desc': '顶尖学科，竞争极其激烈'},
    'A': {'score': 50, 'desc': '一流学科，竞争非常激烈'},
    'B+': {'score': 60, 'desc': '优秀学科，竞争激烈'},
    'B': {'score': 70, 'desc': '良好学科，竞争较激烈'},
    'C+': {'score': 80, 'desc': '一般学科，竞争适中'},
    'C': {'score': 90, 'desc': '基础学科，竞争低'},
    '未评级': {'score': 95, 'desc': '新兴学科，竞争很低'}
}

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
        "enrollment": SCORE_WEIGHTS['录取规模'] / 100,
        "school_reputation": SCORE_WEIGHTS['学校知名度'] / 100,
        "major_reputation": SCORE_WEIGHTS['专业知名度'] / 100
    }

    # 确保权重总和为1
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-6, "权重总和必须为1"

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
        # 获取当前日期
        today = date.today()
        
        # 获取考研日期
        exam_year = today.year if today.month < 9 else today.year + 1
        exam_date = date(exam_year, EXAM_MONTH, EXAM_DAY)
        
        # 计算剩余天数
        days_left = (exam_date - today).days
        
        # 根据剩余天数计算得分
        for (min_days, max_days), score_info in PREP_TIME_SCORES.items():
            if min_days <= days_left < max_days:
                return DimensionScore(
                    "备考时间",
                    score_info['score'],
                    self.WEIGHTS["prep_time"],
                    f"{score_info['desc']}(距考研还有{days_left}天)"
                )
        
        # 如果没有匹配的区间，使用默认值
        return DimensionScore(
            "备考时间",
            50,  # 默认中等分数
            self.WEIGHTS["prep_time"],
            f"备考时间一般(距考研还有{days_left}天)"
        )

    def calculate_english_score(self) -> DimensionScore:
        """计算英语基础得分"""
        cet = self.user_info.cet
        
        if "六级" in cet and "优秀" in cet:
            score_info = ENGLISH_LEVEL_SCORES['六级优秀']
        elif "六级" in cet:
            score_info = ENGLISH_LEVEL_SCORES['六级']
        elif "四级" in cet and "优秀" in cet:
            score_info = ENGLISH_LEVEL_SCORES['四级优秀']
        elif "四级" in cet:
            score_info = ENGLISH_LEVEL_SCORES['四级']
        else:
            score_info = ENGLISH_LEVEL_SCORES['其他']
            
        return DimensionScore(
            "英语基础",
            score_info['score'],
            self.WEIGHTS["english"],
            score_info['desc']
        )

    def calculate_major_match_score(self, school_info: SchoolInfo) -> DimensionScore:
        """计算专业匹配度得分"""
        try:
            user_major = self.user_info.major
            target_major = school_info.major
            
            # 专业名称完全一致
            if user_major == target_major:
                return DimensionScore(
                    "专业匹配度",
                    MAJOR_MATCH_SCORES['EXACT'],
                    self.WEIGHTS["major_match"],
                    "专业完全匹配"
                )
            
            # 获取两个专业的考研方向
            user_advance_majors = set(self._get_advance_majors(user_major))  # 转换为set
            target_advance_majors = set(self._get_advance_majors(target_major))  # 转换为set
            
            # 如果两个专业都在对方的考研方向中
            if user_major in target_advance_majors or target_major in user_advance_majors:
                return DimensionScore(
                    "专业匹配度",
                    MAJOR_MATCH_SCORES['IN_DIRECTION'],
                    self.WEIGHTS["major_match"],
                    f"目标专业在考研方向中"
                )
            
            # 检查是否有共同的考研方向
            common_directions = user_advance_majors.intersection(target_advance_majors)
            if common_directions:
                return DimensionScore(
                    "专业匹配度",
                    MAJOR_MATCH_SCORES['IN_DIRECTION'],
                    self.WEIGHTS["major_match"],
                    f"目标专业在考研方向中"
                )
            
            return DimensionScore(
                "专业匹配度",
                MAJOR_MATCH_SCORES['DIFFERENT'],
                self.WEIGHTS["major_match"],
                "跨专业"
            )
        except Exception as e:
            logger.error(f"计算专业匹配度得分时出错: {str(e)}")
            return DimensionScore(
                "专业匹配度",
                MAJOR_MATCH_SCORES['DIFFERENT'],
                self.WEIGHTS["major_match"],
                "跨专业"
            )

    def calculate_competition_score(self, school_info: SchoolInfo) -> DimensionScore:
        """计算竞争强度得分"""
        try:
            # 获取基于排名的默认分数
            rank_defaults = self._get_rank_based_default_scores(school_info.school_name)
            
            if not school_info.blb:
                # 使用基于排名的默认分数
                return DimensionScore(
                    "竞争强度",
                    rank_defaults["competition"],
                    self.WEIGHTS["competition"],
                    f"{rank_defaults['description_prefix']}竞争较为激烈"
                )
            
            latest_blb = school_info.blb[-1]
            # 安全地获取报考人数和录取人数
            bk = float(latest_blb.get('bk', 0))
            lq = float(latest_blb.get('lq', 1))  # 默认值为1避免除以0
            
            ratio = bk / lq if lq > 0 else 10
            
            for (min_ratio, max_ratio), score_info in COMPETITION_RATIO_SCORES.items():
                if min_ratio <= ratio < max_ratio:
                    description = f"{score_info['desc']}(报录比 {ratio:.1f}:1)"
                    # 添加排名信息到描述中
                    if rank_defaults["description_prefix"]:
                        description = f"{rank_defaults['description_prefix']}{description}"
                    
                    return DimensionScore(
                        "竞争强度",
                        score_info['score'],
                        self.WEIGHTS["competition"],
                        description
                    )
            
            # 如果没有匹配的区间，使用基于排名的默认值
            return DimensionScore(
                "竞争强度",
                rank_defaults["competition"],
                self.WEIGHTS["competition"],
                f"{rank_defaults['description_prefix']}竞争情况未知"
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
        """计算学校跨度得分"""
        try:
            # 获取基于排名的默认分数
            rank_defaults = self._get_rank_based_default_scores(school_info.school_name)
            
            # 获取用户本科学校和目标学校的软科排名
            user_school = self.user_info.school
            target_school = school_info.school_name
            
            logger.info(f"计算学校跨度: 用户学校={user_school}, 目标学校={target_school}")
            
            # 获取学校数据
            user_school_data = get_school_data(user_school)
            target_school_data = get_school_data(target_school)
            
            # 记录获取到的学校数据情况
            logger.info(f"用户学校数据: {user_school_data}")
            logger.info(f"目标学校数据: {target_school_data}")
            
            # 设置默认排名
            DEFAULT_RANK = 500
            
            # 获取用户学校排名，如果没有则使用默认值
            user_rank = DEFAULT_RANK
            if user_school_data and user_school_data.rank is not None:
                user_rank = user_school_data.rank
            else:
                logger.warning(f"用户学校 {user_school} 没有排名数据，使用默认排名 {DEFAULT_RANK}")
            
            # 获取目标学校排名，如果没有则使用默认值
            target_rank = DEFAULT_RANK
            if target_school_data and target_school_data.rank is not None:
                target_rank = target_school_data.rank
            else:
                logger.warning(f"目标学校 {target_school} 没有排名数据，使用默认排名 {DEFAULT_RANK}")
            
            logger.info(f"使用排名计算跨度: 用户学校排名={user_rank}, 目标学校排名={target_rank}")
            
            # 计算排名差距
            rank_gap = target_rank - user_rank
            
            # 如果目标学校排名更好（数值更小），则跨度为负，难度更大
            if rank_gap < 0:
                # 跨度越大（负值越大），分数越低（难度越大）
                gap_score = max(40, 80 + rank_gap / 10)  # 限制最低分为40
                description = f"目标学校排名高于本科学校{abs(rank_gap)}位，难度较大"
            else:
                # 跨度为正（目标学校排名更差），分数越高（难度越小）
                gap_score = min(95, 80 + rank_gap / 20)  # 限制最高分为95
                description = f"目标学校排名低于本科学校{rank_gap}位，难度较小"
            
            # 添加排名信息到描述中
            if rank_defaults["description_prefix"]:
                description = f"{rank_defaults['description_prefix']}{description}"
            
            logger.info(f"排名跨度计算结果: gap_score={gap_score}, description={description}")
            
            return DimensionScore(
                "学校跨度",
                gap_score,
                self.WEIGHTS["school_gap"],
                description
            )
        except Exception as e:
            logger.error(f"计算学校跨度得分时出错: {str(e)}")
            logger.exception("详细错误信息")
            # 返回基于排名的默认值
            rank_defaults = self._get_rank_based_default_scores(school_info.school_name)
            return DimensionScore(
                "学校跨度",
                rank_defaults["school_gap"],
                self.WEIGHTS["school_gap"],
                f"{rank_defaults['description_prefix']}学校跨度适中"
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
        try:
            # 获取基于排名的默认分数
            rank_defaults = self._get_rank_based_default_scores(school_info.school_name)
            
            total_enrollment = 0
            # 计算nlqrs
            nlqrs = 0
            for direction in school_info.directions:
                try:
                    zsrs = direction.get('zsrs', '')
                    # 提取数字字符
                    num_str = ''.join(c for c in zsrs if c.isdigit())
                    if num_str:
                        nlqrs += int(num_str)
                except Exception as e:
                    logger.error(f"处理招生人数时出错: {str(e)}, zsrs={direction.get('zsrs')}")
                    continue
            
            total_enrollment = nlqrs
            
            # 如果没有招生人数数据，使用基于排名的默认值
            if total_enrollment == 0:
                return DimensionScore(
                    "录取规模",
                    rank_defaults["enrollment"],
                    self.WEIGHTS["enrollment"],
                    f"{rank_defaults['description_prefix']}录取规模未知"
                )
            
            # 遍历所有规模区间
            for (min_size, max_size), score_info in ENROLLMENT_SIZE_SCORES.items():
                if min_size <= total_enrollment < max_size:
                    description = f"{score_info['desc']}({total_enrollment}人)"
                    # 添加排名信息到描述中
                    if rank_defaults["description_prefix"]:
                        description = f"{rank_defaults['description_prefix']}{description}"
                    
                    return DimensionScore(
                        "录取规模",
                        score_info['score'],
                        self.WEIGHTS["enrollment"],
                        description
                    )
            
            # 如果没有匹配的区间，使用基于排名的默认值
            return DimensionScore(
                "录取规模",
                rank_defaults["enrollment"],
                self.WEIGHTS["enrollment"],
                f"{rank_defaults['description_prefix']}录取规模未知({total_enrollment}人)"
            )
        except Exception as e:
            logger.error(f"计算录取规模得分时出错: {str(e)}")
            # 返回默认值
            return DimensionScore(
                "录取规模",
                ENROLLMENT_SIZE_SCORES[(0, 10)]['score'],
                self.WEIGHTS["enrollment"],
                "录取规模未知"
            )
            
    def calculate_school_reputation_score(self, school_info: SchoolInfo) -> DimensionScore:
        """计算学校知名度得分"""
        try:
            school_data = get_school_data(school_info.school_name)
            
            if not school_data or school_data.rank is None:
                return DimensionScore(
                    "学校知名度",
                    80,  # 默认中等分数
                    self.WEIGHTS["school_reputation"],
                    "学校知名度数据缺失"
                )
                
            rank = school_data.rank
            
            # 遍历所有排名区间
            for (min_rank, max_rank), score_info in SCHOOL_REPUTATION_SCORES.items():
                if min_rank <= rank <= max_rank:
                    return DimensionScore(
                        "学校知名度",
                        score_info['score'],
                        self.WEIGHTS["school_reputation"],
                        f"{score_info['desc']}(排名第{rank})"
                    )
            
            # 如果排名超出定义的区间，使用最低区间的分数
            return DimensionScore(
                "学校知名度",
                SCHOOL_REPUTATION_SCORES[(501, 1000)]['score'],
                self.WEIGHTS["school_reputation"],
                f"普通院校(排名第{rank})"
            )
        except Exception as e:
            logger.error(f"计算学校知名度得分时出错: {str(e)}")
            return DimensionScore(
                "学校知名度",
                80,  # 默认中等分数
                self.WEIGHTS["school_reputation"],
                "学校知名度数据缺失"
            )
            
    def calculate_major_reputation_score(self, school_info: SchoolInfo) -> DimensionScore:
        """计算专业知名度得分"""
        try:
            major_data = get_major_data(school_info.school_name, school_info.major_code)
            
            if not major_data or major_data.level is None:
                return DimensionScore(
                    "专业知名度",
                    80,  # 默认中等分数
                    self.WEIGHTS["major_reputation"],
                    "专业知名度数据缺失"
                )
                
            level = major_data.level
            
            # 获取对应等级的分数
            if level in MAJOR_REPUTATION_SCORES:
                score_info = MAJOR_REPUTATION_SCORES[level]
                return DimensionScore(
                    "专业知名度",
                    score_info['score'],
                    self.WEIGHTS["major_reputation"],
                    f"{score_info['desc']}(学科评估{level})"
                )
            
            # 如果等级不在定义的范围内，使用最低等级的分数
            return DimensionScore(
                "专业知名度",
                MAJOR_REPUTATION_SCORES['未评级']['score'],
                self.WEIGHTS["major_reputation"],
                f"基础学科(学科评估{level})"
            )
        except Exception as e:
            logger.error(f"计算专业知名度得分时出错: {str(e)}")
            return DimensionScore(
                "专业知名度",
                80,  # 默认中等分数
                self.WEIGHTS["major_reputation"],
                "专业知名度数据缺失"
            )

    def calculate_probability(self, total_score: float) -> float:
        """将总分转换为概率，增加差异性"""
        # 使用更陡峭的S曲线，增加分数差异对概率的影响
        # 原公式: 1 / (1 + math.exp(-0.02 * (total_score - 60))) * 100
        # 新公式: 1 / (1 + math.exp(-0.05 * (total_score - 65))) * 100
        
        # 增加斜率参数从0.02到0.05，使曲线更陡峭
        # 将中点从60调整到65，使得中等难度的分数对应的概率更低
        return 1 / (1 + math.exp(-0.1 * (total_score - 65))) * 100

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
            self.calculate_enrollment_score(school_info),
            self.calculate_school_reputation_score(school_info),  # 新增学校知名度
            self.calculate_major_reputation_score(school_info)    # 新增专业知名度
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

    def _get_rank_based_default_scores(self, school_name: str) -> dict:
        """
        根据学校排名获取各维度的默认分数
        排名越高的学校，默认分数越低（表示竞争越激烈）
        
        Args:
            school_name: 学校名称
            
        Returns:
            包含各维度默认分数的字典
        """
        try:
            # 获取学校排名数据
            school_data = get_school_data(school_name)
            school_rank = 500  # 默认排名
            if school_data and school_data.rank is not None:
                school_rank = school_data.rank
            
            # 根据排名设置默认分数
            if school_rank <= 2:
                return {
                    "competition": 30,  # 竞争非常激烈
                    "enrollment": 40,   # 录取规模较小
                    "school_gap": 30,   # 学校跨度大
                    "major_match": 60,  # 专业匹配要求高
                    "description_prefix": "顶尖名校，"
                }
            if school_rank <= 5:  # 顶尖名校（清北复交浙）
                return {
                    "competition": 40,  # 竞争非常激烈
                    "enrollment": 50,   # 录取规模较小
                    "school_gap": 40,   # 学校跨度大
                    "major_match": 60,  # 专业匹配要求高
                    "description_prefix": "顶尖名校，"
                }
            elif school_rank <= 20:  # 一流名校
                return {
                    "competition": 50,
                    "enrollment": 60,
                    "school_gap": 50,
                    "major_match": 70,
                    "description_prefix": "一流名校，"
                }
            elif school_rank <= 50:  # 知名高校
                return {
                    "competition": 60,
                    "enrollment": 70,
                    "school_gap": 60,
                    "major_match": 75,
                    "description_prefix": "知名高校，"
                }
            elif school_rank <= 100:  # 较知名高校
                return {
                    "competition": 70,
                    "enrollment": 75,
                    "school_gap": 70,
                    "major_match": 80,
                    "description_prefix": "较知名高校，"
                }
            elif school_rank <= 200:  # 普通高校
                return {
                    "competition": 80,
                    "enrollment": 80,
                    "school_gap": 80,
                    "major_match": 85,
                    "description_prefix": "普通高校，"
                }
            else:  # 一般院校
                return {
                    "competition": 90,
                    "enrollment": 85,
                    "school_gap": 90,
                    "major_match": 90,
                    "description_prefix": ""
                }
        except Exception as e:
            logger.error(f"获取基于排名的默认分数时出错: {str(e)}")
            # 返回中等水平的默认值
            return {
                    "competition": 90,
                    "enrollment": 85,
                    "school_gap": 90,
                    "major_match": 90,
                    "description_prefix": ""
                }