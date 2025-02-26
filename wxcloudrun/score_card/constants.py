"""评分卡相关常量"""
from wxcloudrun.score_card.city_data_loader import CITY_SCORES

# 学校层次
SCHOOL_LEVELS = {
    'C9': 4,
    '985': 3,
    '211': 2,
    '一本': 1,
    '其他': 0
}

# 分数权重
SCORE_WEIGHTS = {
    '备考时间': 5,
    '英语基础': 5,
    '专业匹配度': 20,
    '竞争强度': 20,
    '录取规模': 10,
    '学校跨度': 30,
    '专业排名': 10
}

# 专业排名分数对应表
RANK_SCORES = {
    10: 10,  # 前10%
    20: 8,   # 前20%
    50: 5,   # 前50%
    100: 0   # 其他
}

# 城市生活成本等级（示例数据）
CITY_LIVING_COST = {
    '北京': 5,  # 最高
    '上海': 5,
    '深圳': 5,
    '广州': 4,
    '杭州': 4,
    # ... 其他城市
}

# 城市教育资源等级（示例数据）
CITY_EDUCATION_RESOURCE = {
    '北京': 5,
    '上海': 5,
    '南京': 4,
    '武汉': 4,
    # ... 其他城市
}

# 城市医疗资源等级（示例数据）
CITY_MEDICAL_RESOURCE = {
    '北京': 5,
    '上海': 5,
    '广州': 4,
    '成都': 4,
    # ... 其他城市
}

# 地理位置评分权重（0-1之间，总和为1）
LOCATION_SCORE_WEIGHTS = {
    '生活成本': 0.15,        # 生活成本影响较大，但不是最主要因素
    '家乡匹配度': 0.25,      # 与家庭联系的便利程度很重要
    '教育资源': 0.20,        # 教育资源对学习环境有重要影响
    '医疗资源': 0.15,        # 医疗资源保障基本生活质量
    '工作城市匹配度': 0.25   # 未来发展前景很重要
}

# 确保权重总和为1
assert abs(sum(LOCATION_SCORE_WEIGHTS.values()) - 1.0) < 1e-6, "地理位置评分权重总和必须为1"

# 在文件中添加缺失值常量
LOCATION_SCORE_DEFAULTS = {
    '生活成本': 50.0,      # 中等生活成本
    '家乡匹配度': 40.0,    # 稍低于中等，因为跨地区求学比较常见
    '教育资源': 50.0,      # 中等教育资源
    '医疗资源': 50.0,      # 中等医疗资源
    '工作城市匹配度': 40.0 # 稍低于中等，因为跨地区就业比较常见
}

# 家乡匹配度得分配置
HOMETOWN_MATCH_SCORES = {
    'SAME_CITY': 100.0,    # 同城
    'SAME_PROVINCE': 70.0, # 同省不同城
    'DIFFERENT': 40.0      # 不同省
}

# 工作城市匹配度得分配置
WORK_CITY_MATCH_SCORES = {
    'CITY_MATCH': 100.0,    # 学校所在城市是意向工作城市之一
    'PROVINCE_MATCH': 70.0, # 学校所在省份包含意向工作城市
    'NO_MATCH': 40.0        # 无匹配
}

# 学校专业评分权重（0-1之间，总和为1）
MAJOR_SCORE_WEIGHTS = {
    '学校知名度': 0.3,
    '专业排名': 0.3,
    '学校综合满意度': 0.2,
    '专业综合满意度': 0.2
}

# 确保权重总和为1
assert abs(sum(MAJOR_SCORE_WEIGHTS.values()) - 1.0) < 1e-6, "学校专业评分权重总和必须为1"

# 学校专业评分默认值
MAJOR_SCORE_DEFAULTS = {
    '学校知名度': 50.0,        # 中等知名度
    '专业排名': 50.0,          # 中等排名
    '学校综合满意度': 50.0,    # 中等满意度
    '专业综合满意度': 50.0     # 中等满意度
}

# 学校知名度得分配置
SCHOOL_REPUTATION_SCORES = {
    'C9': 100.0,     # C9高校
    '985': 90.0,     # 非C9的985高校
    '211': 80.0,     # 非985的211高校
    '双一流': 70.0,  # 非211的双一流高校
    'UNKNOWN': 30.0, # 未知等级
    'OTHER': 50.0    # 其他高校
}

# 专业排名得分配置
MAJOR_RANK_SCORES = {
    'TOP_5': 100.0,   # 全国前5名
    'TOP_10': 90.0,   # 全国前6-10名
    'TOP_20': 80.0,   # 全国前11-20名
    'TOP_50': 70.0,   # 全国前21-50名
    'OTHER': 50.0     # 其他排名
}

# 学校层次得分配置
SCHOOL_LEVEL_SCORES = {
    'C9': 100.0,    # C9高校
    '985': 90.0,    # 非C9的985高校
    '211': 80.0,    # 非985的211高校
    '双一流': 70.0, # 非211的双一流高校
    'OTHER': 50.0   # 其他高校
}

# 学科等级得分配置
XUEKE_LEVEL_SCORES = {
    'A+': 100.0,  # A+级学科
    'A': 90.0,    # A级学科
    'A-': 80.0,   # A-级学科
    'B+': 70.0,   # B+级学科
    'B': 60.0,    # B级学科
    'B-': 50.0,   # B-级学科
    'UNKNOWN': 30.0,  # 未评级或未知等级
    'OTHER': 40.0     # 其他评级
}

# 满意度分数区间配置（0-5分制转换为0-100分制）
SATISFACTION_SCORE_RANGES = {
    (4.5, 5.0): 100.0,  # 极高满意度
    (4.0, 4.5): 90.0,   # 很高满意度
    (3.5, 4.0): 80.0,   # 较高满意度
    (3.0, 3.5): 70.0,   # 中等偏上满意度
    (2.5, 3.0): 60.0,   # 中等满意度
    (2.0, 2.5): 50.0,   # 中等偏下满意度
    (1.5, 2.0): 40.0,   # 较低满意度
    (1.0, 1.5): 30.0,   # 很低满意度
    (0.0, 1.0): 20.0    # 极低满意度
}

# 概率等级阈值
PROBABILITY_LEVELS = {
    'IMPOSSIBLE': 25,  # <25%
    'DIFFICULT': 45,  # 25-45%
    'MODERATE': 75,  # 45-75%
    'EASY': 95,      # 75-95%
}

# 专业匹配度分数
MAJOR_MATCH_SCORES = {
    'EXACT': 100,    # 完全匹配
    'IN_DIRECTION': 80,  # 在考研方向中
    'DIFFERENT': 40  # 不相关专业
}

# 报录比分数区间
COMPETITION_RATIO_SCORES = {
    (0, 3): {'score': 90, 'desc': '竞争较小'},
    (3, 5): {'score': 70, 'desc': '竞争适中'},
    (5, 8): {'score': 50, 'desc': '竞争激烈'},
    (8, 10): {'score': 30, 'desc': '竞争非常激烈'},
    (10, float('inf')): {'score': 10, 'desc': '竞争极其激烈'}
}

# 招生规模分数
ENROLLMENT_SIZE_SCORES = {
    (200, float('inf')): {'score': 100, 'desc': '招生规模大'},
    (100, 200): {'score': 80, 'desc': '招生规模中等'},
    (30, 50): {'score': 50, 'desc': '招生规模一般'},
    (0, 10): {'score': 20, 'desc': '招生规模小'}
}

# 备考时间分数 (按天数计算)
PREP_TIME_SCORES = {
    (0, 90): {'score': 30, 'desc': '备考时间较短'},      # 0-3个月
    (90, 180): {'score': 60, 'desc': '备考时间一般'},    # 3-6个月
    (180, 270): {'score': 80, 'desc': '备考时间充足'},   # 6-9个月
    (270, 365): {'score': 90, 'desc': '备考时间很充足'},  # 9-12个月
    (365, float('inf')): {'score': 100, 'desc': '备考时间非常充足'} # 12个月以上
}

# 英语水平分数
ENGLISH_LEVEL_SCORES = {
    'CET6': {'score': 80, 'desc': '已过六级'},
    'CET4': {'score': 60, 'desc': '已过四级'},
    'NONE': {'score': 40, 'desc': '未过四六级'}
}

# 专业排名分数
MAJOR_RANKING_SCORES = {
    'TOP10': {'score': 100, 'desc': '专业前10%'},
    'TOP20': {'score': 80, 'desc': '专业前20%'},
    'TOP50': {'score': 60, 'desc': '专业前50%'},
    'OTHER': {'score': 40, 'desc': '专业排名较后'}
}

# 学校跨度分数
SCHOOL_GAP_SCORES = {
    -1: {'score': 100, 'desc': '目标学校档次高于用户学校档次'},
    -2: {'score': 80, 'desc': '目标学校档次高于用户学校档次'},
    2: {'score': 20, 'desc': '跨度较大'},
    1: {'score': 40, 'desc': '跨度适中'},
    0: {'score': 60, 'desc': '基本持平'}
}

# 年级对应的备考月数
GRADE_PREP_MONTHS = {
    '大一': 39,
    '大二': 27, 
    '大三': 15,
    '大四': 4  # 假设9月开学,到12月考试约4个月
}

# 考研日期配置
EXAM_DAY = 23  # 每年12月23日

# 专业数据文件路径
MAJOR_DETAIL_FILE = 'resources/major_detail_flat.json'

# 竞争强度默认值配置
COMPETITION_DEFAULT_SCORE = {
    'score': 50,
    'desc': '无报录比数据'
}

# 升学维度评分权重
ADVANCED_STUDY_WEIGHTS = {
    '升学率': 0.4,
    '升学人数': 0.2,
    '升学率增长': 0.2,
    '留学质量': 0.2
}

# 评分等级划分
SCORE_LEVELS = {
    'high': {
        'threshold': 80,
        'descriptions': {
            # 升学深造维度
            '升学率': '该校升学深造率处于全国前20%，升学机会优秀',
            '升学人数': '该校升学深造人数规模较大，升学机会充足',
            '升学率增长': '该校升学深造率呈现良好的增长趋势',
            '留学质量': '该校赴美留学比例处于全国前20%，留学质量优秀',
            # 专业维度
            '学校知名度': '该校在该专业领域知名度很高，就业优势明显',
            '专业排名': '该专业排名靠前，实力较强',
            '学校综合满意度': '该校综合满意度高，学习体验好',
            '专业综合满意度': '该专业综合满意度高，专业建设完善'
        }
    },
    'medium': {
        'threshold': 60,
        'descriptions': {
            # 升学深造维度
            '升学率': '该校升学深造率处于全国中等水平，升学机会良好',
            '升学人数': '该校升学深造人数规模适中，升学机会一般',
            '升学率增长': '该校升学深造率保持稳定',
            '留学质量': '该校赴美留学比例处于全国中等水平，留学质量良好',
            # 专业维度
            '学校知名度': '该校在该专业领域知名度适中，就业前景良好',
            '专业排名': '该专业排名中等，发展潜力好',
            '学校综合满意度': '该校综合满意度良好，学习体验尚可',
            '专业综合满意度': '该专业综合满意度良好，专业发展稳定'
        }
    },
    'low': {
        'threshold': 0,
        'descriptions': {
            # 升学深造维度
            '升学率': '该校升学深造率处于全国后40%，升学机会较少',
            '升学人数': '该校升学深造人数规模较小，升学机会有限',
            '升学率增长': '该校升学深造率增长较慢',
            '留学质量': '该校赴美留学比例处于全国后40%，留学质量一般',
            # 专业维度
            '学校知名度': '该校在该专业领域知名度一般，需要自身努力',
            '专业排名': '该专业排名靠后，需要谨慎选择',
            '学校综合满意度': '该校综合满意度一般，仍有提升空间',
            '专业综合满意度': '该专业综合满意度一般，建设有待加强'
        }
    }
}

# 评分卡总分权重
SCORE_CARD_WEIGHTS = {
    'major_card': 0.5,           # 专业评分权重
    'location_card': 0.25,       # 地理位置评分权重
    'employment_card': 0.25,     # 就业评分权重
    'advanced_study_card': 0.25  # 升学评分权重
}

# 总评分权重
TOTAL_SCORE_WEIGHTS = {
    'admission_probability': 0.33,  # 录取概率
    'score_card': 0.67             # 评分卡总分
}

# 录取评分权重
ADMISSION_SCORE_WEIGHTS = {
    '备考时间': 0.15,
    '英语基础': 0.15,
    '专业匹配度': 0.20,
    '竞争强度': 0.20,
    '录取规模': 0.10,
    '学校跨度': 0.10,
    '专业排名': 0.10
}

# 录取评分默认值
ADMISSION_SCORE_DEFAULTS = {
    '备考时间': 0,
    '英语基础': 0,
    '专业匹配度': 5,
    '竞争强度': 50,
    '录取规模': 5,
    '学校跨度': 0,
    '专业排名': 0
}

# 录取评分等级
ADMISSION_SCORE_LEVELS = {
    'high': {
        'threshold': 80,
        'descriptions': {
            '备考时间': '备考时间充足',
            '英语基础': '英语基础扎实',
            '专业匹配度': '专业高度匹配',
            '竞争强度': '竞争压力较小',
            '录取规模': '录取名额充足',
            '学校跨度': '学校层次合适',
            '专业排名': '专业排名靠前'
        }
    },
    'medium': {
        'threshold': 60,
        'descriptions': {
            '备考时间': '备考时间一般',
            '英语基础': '英语基础一般',
            '专业匹配度': '专业基本匹配',
            '竞争强度': '竞争压力适中',
            '录取规模': '录取名额一般',
            '学校跨度': '学校层次跨度较大',
            '专业排名': '专业排名中等'
        }
    },
    'low': {
        'threshold': 0,
        'descriptions': {
            '备考时间': '备考时间不足',
            '英语基础': '英语基础薄弱',
            '专业匹配度': '专业匹配度低',
            '竞争强度': '竞争压力较大',
            '录取规模': '录取名额有限',
            '学校跨度': '学校层次跨度过大',
            '专业排名': '专业排名靠后'
        }
    }
}

# 非体制就业评分权重
NON_SYSTEM_EMPLOYMENT_SCORE_WEIGHTS = {
    "employment_rate": 0.4,      # 就业率权重
    "school_satisfaction": 0.3,  # 学校环境满意度权重
    "major_satisfaction": 0.3    # 专业就业满意度权重
}

# 非体制就业评分默认值
NON_SYSTEM_EMPLOYMENT_SCORE_DEFAULTS = {
    "employment_rate": 50,      # 就业率默认分
    "school_satisfaction": 50,  # 学校环境满意度默认分
    "major_satisfaction": 50    # 专业就业满意度默认分
}

# 非体制就业评分等级描述
NON_SYSTEM_EMPLOYMENT_LEVELS = {
    'high': {
        'threshold': 80,
        'descriptions': {
            '就业率': '就业率优秀',
            '学校满意度': '学校就业环境优秀',
            '专业满意度': '专业就业前景优秀'
        }
    },
    'medium': {
        'threshold': 60,
        'descriptions': {
            '就业率': '就业率良好',
            '学校满意度': '学校就业环境良好',
            '专业满意度': '专业就业前景良好'
        }
    },
    'low': {
        'threshold': 0,
        'descriptions': {
            '就业率': '就业率一般',
            '学校满意度': '学校就业环境一般',
            '专业满意度': '专业就业前景一般'
        }
    }
}

# 满意度评分权重
SATISFACTION_SCORE_WEIGHTS = {
    "school_satisfaction": 0.25,  # 学校综合满意度权重
    "major_satisfaction": 0.25,   # 专业综合满意度权重
    "school_reputation": 0.25,    # 学校知名度权重
    "major_ranking": 0.25         # 专业排名权重
}

# 满意度评分默认值
SATISFACTION_SCORE_DEFAULTS = {
    "school_satisfaction": 50,  # 学校综合满意度默认分
    "major_satisfaction": 50,   # 专业综合满意度默认分
    "school_reputation": 50,    # 学校知名度默认分
    "major_ranking": 50         # 专业排名默认分
}

# 学科评估等级分数映射
LEVEL_SCORES = {
    "A+": 95,
    "A": 85,
    "A-": 75,
    "B+": 65,
    "B": 55,
    "B-": 45,
    "C+": 35,
    "C": 25,
    "C-": 15
}

# 体制内就业评分权重
SYSTEM_EMPLOYMENT_SCORE_WEIGHTS = {
    "civil_servant": 0.4,    # 公务员占比权重
    "institution": 0.3,      # 事业单位占比权重
    "state_owned": 0.3       # 国企占比权重
}

# 体制内就业评分默认值
SYSTEM_EMPLOYMENT_SCORE_DEFAULTS = {
    "civil_servant": 50,    # 公务员占比默认分
    "institution": 50,      # 事业单位占比默认分
    "state_owned": 50       # 国企占比默认分
}

# 体制内就业评分等级描述
SYSTEM_EMPLOYMENT_LEVELS = {
    'high': {
        'threshold': 80,
        'descriptions': {
            '公务员': '公务员就业前景优秀',
            '事业单位': '事业单位就业前景优秀',
            '国企': '国企就业前景优秀'
        }
    },
    'medium': {
        'threshold': 60,
        'descriptions': {
            '公务员': '公务员就业前景良好',
            '事业单位': '事业单位就业前景良好',
            '国企': '国企就业前景良好'
        }
    },
    'low': {
        'threshold': 0,
        'descriptions': {
            '公务员': '公务员就业前景一般',
            '事业单位': '事业单位就业前景一般',
            '国企': '国企就业前景一般'
        }
    }
}

# 升学评分权重
ADVANCED_STUDY_SCORE_WEIGHTS = {
    "further_study_rate": 0.3,     # 升学率权重
    "further_study_number": 0.3,   # 升学人数权重
    "abroad_study_ratio": 0.2,     # 出国留学占比权重
    "us_study_ratio": 0.2          # 美国留学占比权重
}

# 升学评分默认值
ADVANCED_STUDY_SCORE_DEFAULTS = {
    "further_study_rate": 50,     # 升学率默认分
    "further_study_number": 50,   # 升学人数默认分
    "abroad_study_ratio": 50,     # 出国留学占比默认分
    "us_study_ratio": 50          # 美国留学占比默认分
}

# 升学评分等级描述
ADVANCED_STUDY_LEVELS = {
    'high': {
        'threshold': 80,
        'descriptions': {
            '升学率': '升学率优秀',
            '升学人数': '升学人数众多',
            '出国留学占比': '出国留学机会丰富',
            '美国留学占比': '美国留学机会丰富'
        }
    },
    'medium': {
        'threshold': 60,
        'descriptions': {
            '升学率': '升学率良好',
            '升学人数': '升学人数适中',
            '出国留学占比': '出国留学机会良好',
            '美国留学占比': '美国留学机会良好'
        }
    },
    'low': {
        'threshold': 0,
        'descriptions': {
            '升学率': '升学率一般',
            '升学人数': '升学人数较少',
            '出国留学占比': '出国留学机会有限',
            '美国留学占比': '美国留学机会有限'
        }
    }
} 