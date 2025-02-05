from datetime import datetime
import json
import os

# 全局变量存储加载的数据
SCHOOL_LEVELS = {}
MAJOR_DETAILS = {}
BLB_AVERAGES = {}

def load_school_levels() -> dict:
    """加载学校等级数据"""
    global SCHOOL_LEVELS
    if SCHOOL_LEVELS:  # 如果已经加载过，直接返回
        return SCHOOL_LEVELS
        
    try:
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        cur_dir = os.path.dirname(cur_dir)
        file_path = os.path.join(cur_dir, 'resources/school_level.json')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                school = json.loads(line.strip())
                SCHOOL_LEVELS[school["学校名称"]] = school
            return SCHOOL_LEVELS
    except Exception as e:
        print(f"加载学校数据失败: {e}")
        return {}

def load_major_details() -> dict:
    """加载专业详细信息"""
    global MAJOR_DETAILS
    if MAJOR_DETAILS:  # 如果已经加载过，直接返回
        return MAJOR_DETAILS
        
    try:
        file_path = os.path.join(os.path.dirname(__file__), '../resources/major_detail_flat.json')
        major_dict = {}
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                major_info = json.loads(line.strip())
                major_dict[major_info["专业名称"]] = major_info
        MAJOR_DETAILS = major_dict
        return MAJOR_DETAILS
    except Exception as e:
        print(f"加载专业数据失败: {e}")
        return {}

def load_blb_averages() -> dict:
    """加载报录比默认值数据"""
    global BLB_AVERAGES
    if BLB_AVERAGES:  # 如果已经加载过，直接返回
        return BLB_AVERAGES
        
    try:
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        cur_dir = os.path.dirname(cur_dir)
        file_path = os.path.join(cur_dir, 'resources/blb_averages.json')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                school_data = json.loads(line.strip())
                BLB_AVERAGES[school_data["school"]] = school_data
        return BLB_AVERAGES
    except Exception as e:
        print(f"加载报录比默认值数据失败: {e}")
        return {}

# 初始化加载数据
SCHOOL_LEVELS = load_school_levels()
MAJOR_DETAILS = load_major_details()
BLB_AVERAGES = load_blb_averages()

class AdmissionScoreCard:
    def __init__(self, user_info: dict, target_info: dict):
        self.user_info = user_info
        self.target_info = target_info
        self.total_score = 0
        
    def _get_school_level(self, school_name: str) -> int:
        """获取学校等级，返回数字等级（越高等级越高）"""
        school_info = SCHOOL_LEVELS.get(school_name, {})
        if school_info.get("是否C9") == "是":
            return 4
        elif school_info.get("是否985") == "是":
            return 3
        elif school_info.get("是否211") == "是":
            return 2
        elif school_info.get("是否一本") == "是":
            return 1
        return 0
        
    def calculate_preparation_time_score(self) -> float:
        """计算备考时间得分"""
        current_date = datetime.now()
        grade = self.user_info.get("grade", "").lower()
        
        # 获取最近的考研时间
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
        
        # 考研时间通常在12月22-24日左右，这里统一设为23日
        exam_date = datetime.strptime(f"{exam_year}-12-23", "%Y-%m-%d")
        
        # 如果当前日期已经过了今年的考研时间，就算下一年的
        if current_date > exam_date:
            exam_date = datetime.strptime(f"{exam_year + 1}-12-23", "%Y-%m-%d")
        
        days_until_exam = (exam_date - current_date).days
        if days_until_exam > 0:
            return min(days_until_exam // 15, 25)  # 每15天1分，最多25分
        return 0
        
    def calculate_english_score(self) -> float:
        """计算英语基础得分"""
        english_level = self.user_info.get("english_level", "")
        if "六级" in english_level:
            return 5
        elif "四级" in english_level:
            return 2
        return 0
        
    def _get_advance_majors(self, major_name: str) -> set:
        """获取专业的考研方向列表"""
        major_info = MAJOR_DETAILS.get(major_name, {})
        advance_majors = set()
        
        if "考研方向" in major_info:
            for direction in major_info["考研方向"]:
                if direction.get("zymc"):
                    advance_majors.add(direction["zymc"])
        
        return advance_majors

    def calculate_major_match_score(self, school_info: dict = None) -> float:
        """
        计算专业匹配度得分
        完全一致：20分
        考研方向相同：10分
        其他情况：5分
        """
        user_major = self.user_info.get("major", "")
        target_major = school_info.get("major", "")
        
        # 专业名称完全一致
        if user_major == target_major:
            return 20
        
        # 获取两个专业的考研方向
        user_advance_majors = self._get_advance_majors(user_major)
        target_advance_majors = self._get_advance_majors(target_major)
        
        # 如果两个专业都在对方的考研方向中
        if user_major in target_advance_majors or target_major in user_advance_majors:
            return 10
        
        # 检查是否有共同的考研方向
        if user_advance_majors and target_advance_majors:
            if user_advance_majors & target_advance_majors:  # 集合交集
                return 10
        
        return 5
        
    def calculate_competition_score(self, school_info: dict = None) -> float:
        """
        计算竞争强度得分
        使用历年报录比的平均值 * 20 计算得分
        报录比越高，得分越高，最高20分
        如果没有实际数据，使用默认值：
        1. 优先使用院系默认值
        2. 如果没有院系默认值，使用学校默认值
        3. 如果都没有，返回默认分数5分
        """
        if not school_info:
            return 5
        
        # 尝试获取实际报录比数据
        if "blb" in school_info and school_info["blb"]:
            blb_list = school_info["blb"]
            total_ratio = 0
            valid_count = 0
            
            for item in blb_list:
                try:
                    ratio_str = item.get("blb", "0%").strip("%")
                    ratio = float(ratio_str)
                    
                    # 剔除大于100的异常值
                    if ratio > 100:
                        continue
                        
                    # 如果报录比大于1，说明是百分比形式，需要再除以100
                    if ratio > 1:
                        ratio = ratio / 100
                        
                    total_ratio += ratio
                    valid_count += 1
                except (ValueError, TypeError):
                    continue
            
            if valid_count > 0:
                avg_ratio = total_ratio / valid_count
                return min(20, avg_ratio * 20)
        
        # 如果没有实际数据，使用默认值
        school_name = school_info.get("school_name", "")
        department = school_info.get("departments", "")  # 院系名称
        
        if school_name in BLB_AVERAGES:
            school_data = BLB_AVERAGES[school_name]
            # 优先使用院系默认值
            if department and department in school_data:
                ratio = school_data[department]
                return min(20, ratio * 20)
            # 使用学校默认值
            elif "avg" in school_data:
                ratio = school_data["avg"]
                return min(20, ratio * 20)
        
        return 5  # 如果没有任何可用数据，返回默认分数
        
    def _parse_enrollment_count(self, directions: list) -> int:
        """
        解析所有方向的总招生人数
        :param directions: 方向列表
        :return: 总招生人数
        """
        total_count = 0
        if not directions:
            return total_count
        
        for direction in directions:
            zsrs = direction.get("zsrs", "")
            if not zsrs:
                continue
            
            # 处理格式如 "专业：2(不含推免)" 的字符串
            try:
                # 提取数字
                count = int(''.join(filter(str.isdigit, zsrs)))
                total_count += count
            except (ValueError, TypeError):
                continue
            
        return total_count

    def calculate_enrollment_score(self, school_info: dict = None) -> float:
        """
        计算录取规模得分
        每增加10个名额增加两分，最多10分
        """
        if not school_info or "directions" not in school_info:
            return 0
        
        total_enrollment = self._parse_enrollment_count(school_info["directions"])
        return min(10, (total_enrollment // 10) * 2)
        
    def calculate_school_level_score(self, school_info: dict = None) -> float:
        """计算学校跨度得分"""
        user_school = self.user_info.get("school", "")
        target_school = school_info.get("school_name", "")  # 使用当前学校的名称
        
        user_level = self._get_school_level(user_school)
        target_level = self._get_school_level(target_school)
        
        level_diff = target_level - user_level
        
        # 同级院校 +10分；升1档 +5分；升2档以及以上 +0分
        if level_diff == 0:
            return 10
        elif level_diff == 1:
            return 5
        return 0
        
    def calculate_major_rank_score(self) -> float:
        """
        计算专业排名得分
        前10%：10分
        前20%：8分
        前50%：5分
        其他：0分
        """
        major_level = self.user_info.get("major_level", "")
        if not major_level:
            return 0
        
        try:
            # 去掉可能的"前"字和"%"符号
            level_str = major_level.replace("前", "").replace("%", "")
            rank_percentage = float(level_str)
            
            if rank_percentage <= 10:
                return 10
            elif rank_percentage <= 20:
                return 8
            elif rank_percentage <= 50:
                return 5
            return 0
        except (ValueError, TypeError):
            return 0
            
    def calculate_total_score(self, school_info: dict = None) -> dict:
        """
        计算总分
        :return: 包含各维度分数和总分的字典
        """
        scores = {
            "备考时间": self.calculate_preparation_time_score(),
            "英语基础": self.calculate_english_score(),
            "专业匹配度": self.calculate_major_match_score(school_info),
            "竞争强度": self.calculate_competition_score(school_info),
            "录取规模": self.calculate_enrollment_score(school_info),
            "学校跨度": self.calculate_school_level_score(school_info),
            "专业排名": self.calculate_major_rank_score()
        }
        
        # 计算总分
        total_score = sum(scores.values())
        scores["总分"] = total_score
        
        return scores

def get_admission_score(user_info: dict, target_info: dict, 
                       school_info: dict = None) -> dict:
    """
    获取录取评分
    
    :param user_info: 用户信息字典
    :param target_info: 目标院校信息字典
    :param school_info: 学校详细信息字典
    :return: 包含各维度分数和总分的字典
    """
    score_card = AdmissionScoreCard(user_info, target_info)
    return score_card.calculate_total_score(school_info)

# 示例用法
if __name__ == "__main__":
    user_info = {
        "school": "某大学",
        "major": "计算机科学与技术",
        "grade": "15",  # top 15%
        "is_first_time": "是",
        "good_at_subject": "数学",
        "english_level": "六级"
    }
    
    target_info = {
        "school": "清华大学",
        "major": "计算机科学与技术",
        "direction": "人工智能",
        "city": "北京",
        "province": "北京",
        "school_level": "C9"
    }
    
    score = get_admission_score(
        user_info, 
        target_info,
        school_info={
            "blb": [
                {"blb": "0.3%"},
                {"blb": "0.4%"},
                {"blb": "0.5%"},
                {"blb": "0.6%"},
                {"blb": "0.7%"}
            ]
        }
    )
    
    print(f"录取评分: {score}") 