import json
import os
from typing import Dict, List, Tuple, Optional, Any
from loguru import logger
from wxcloudrun.beans.input_models import MergeSchoolData, MergeMajorData
from collections import defaultdict

# 数据模型类
class MergeSchoolData:
    def __init__(self, data: Dict[str, Any]):
        self.school_name = data.get('school_name')
        self.rank = data.get('rank')
        self.overall_satisfaction = data.get('overall_satisfaction')
        self.environment_satisfaction = data.get('environment_satisfaction')
        self.employment_ratio = data.get('employment_ratio')
        self.civil_servant_ratio = data.get('civil_servant_ratio')
        self.institution_ratio = data.get('institution_ratio')
        self.state_owned_ratio = data.get('state_owned_ratio')
        self.further_study_rate = data.get('further_study_rate')
        self.further_study_number = data.get('further_study_number')
        self.abroad_study_ratio = data.get('abroad_study_ratio')
        self.us_study_ratio = data.get('us_study_ratio')

class MergeMajorData:
    def __init__(self, data: Dict[str, Any]):
        self.school_name = data.get('school_name')
        self.major_code = data.get('major_code')
        self.major_name = data.get('major_name')
        self.level = data.get('level')
        self.overall_satisfaction = data.get('overall_satisfaction')
        self.employment_satisfaction = data.get('employment_satisfaction')

# 全局变量存储数据
SCHOOL_DATA: Dict[str, MergeSchoolData] = {}  # key: school_name
MAJOR_DATA: Dict[Tuple[str, str], MergeMajorData] = {}  # key: (school_name, major_code)

# 资源文件路径
RESOURCES_DIR = 'wxcloudrun/resources'
SCHOOL_DATA_FILE = os.path.join(RESOURCES_DIR, 'merged_school_data.jsonl')
MAJOR_DATA_FILE = os.path.join(RESOURCES_DIR, 'merged_major_metrics.jsonl')

def load_data():
    """加载所有需要的数据"""
    global SCHOOL_DATA, MAJOR_DATA
    
    # 检查资源目录是否存在
    if not os.path.exists(RESOURCES_DIR):
        logger.warning(f"资源目录不存在: {RESOURCES_DIR}，尝试创建")
        try:
            os.makedirs(RESOURCES_DIR, exist_ok=True)
        except Exception as e:
            logger.error(f"创建资源目录失败: {str(e)}")
    
    # 加载学校数据
    try:
        if not os.path.exists(SCHOOL_DATA_FILE):
            logger.warning(f"学校数据文件不存在: {SCHOOL_DATA_FILE}")
            # 创建一个空的学校数据文件
            with open(SCHOOL_DATA_FILE, 'w', encoding='utf-8') as f:
                pass
        else:
            with open(SCHOOL_DATA_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    school_name = data.get('school_name')
                    if school_name:
                        SCHOOL_DATA[school_name] = MergeSchoolData(data)
    except Exception as e:
        logger.error(f"加载学校数据失败: {str(e)}")
    
    # 加载专业数据
    try:
        if not os.path.exists(MAJOR_DATA_FILE):
            logger.warning(f"专业数据文件不存在: {MAJOR_DATA_FILE}，将使用测试数据")
            # 添加一些测试数据
            _add_test_major_data()
        else:
            with open(MAJOR_DATA_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    school_name = data.get('school_name')
                    major_code = data.get('major_code')
                    if school_name and major_code:
                        MAJOR_DATA[(school_name, major_code)] = MergeMajorData(data)
    except Exception as e:
        logger.error(f"加载专业数据失败: {str(e)}")
        # 添加一些测试数据
        _add_test_major_data()
    
    logger.info(f"数据加载完成: {len(SCHOOL_DATA)}所学校, {len(MAJOR_DATA)}个专业")

def _add_test_major_data():
    """添加测试专业数据"""
    # 为前100所学校添加测试专业数据
    count = 0
    for school_name in list(SCHOOL_DATA.keys())[:100]:
        # 为每所学校添加3个测试专业
        for i, major_code in enumerate(['0101', '0201', '0301']):
            major_name = f"测试专业{i+1}"
            data = {
                'school_name': school_name,
                'major_code': major_code,
                'major_name': major_name,
                'level': 'A' if i == 0 else ('B' if i == 1 else 'C'),
                'overall_satisfaction': 85 - i * 10,
                'employment_satisfaction': 80 - i * 10
            }
            MAJOR_DATA[(school_name, major_code)] = MergeMajorData(data)
            count += 1
    
    logger.info(f"添加了 {count} 条测试专业数据")

def get_school_data(school_name: str) -> Optional[MergeSchoolData]:
    """获取学校数据
    
    Args:
        school_name: 学校名称
        
    Returns:
        学校数据
    """
    return SCHOOL_DATA.get(school_name)

def get_major_data(school_name: str, major_code: str) -> Optional[MergeMajorData]:
    """获取专业数据
    
    Args:
        school_name: 学校名称
        major_code: 专业代码
        
    Returns:
        专业数据
    """
    return MAJOR_DATA.get((school_name, major_code))

def get_all_school_names() -> List[str]:
    """获取所有学校名称"""
    return list(SCHOOL_DATA.keys())

def get_school_majors(school_name: str) -> List[Tuple[str, str]]:
    """获取指定学校的所有专业代码和名称"""
    majors = []
    for (s_name, major_code), major_data in MAJOR_DATA.items():
        if s_name == school_name:
            majors.append((major_code, major_data.major_name))
    return majors

def get_major_by_name(school_name: str, major_name: str) -> Optional[MergeMajorData]:
    """通过学校名称和专业名称获取专业数据"""
    for (s_name, _), major_data in MAJOR_DATA.items():
        if s_name == school_name and major_data.major_name == major_name:
            return major_data
    return None

def init_data():
    """初始化所有数据"""
    try:
        load_data()
        logger.info("成功初始化所有评分卡数据")
    except Exception as e:
        logger.error(f"初始化评分卡数据时出错: {str(e)}")
        # 不抛出异常，让程序继续运行

def validate_data():
    """验证数据完整性"""
    try:
        # 检查学校数据
        school_count = len(SCHOOL_DATA)
        schools_with_satisfaction = sum(1 for s in SCHOOL_DATA.values() 
                                     if s.overall_satisfaction is not None)
        schools_with_employment = sum(1 for s in SCHOOL_DATA.values() 
                                   if s.employment_ratio is not None)
        
        # 检查专业数据
        unique_schools = len({school for school, _ in MAJOR_DATA.keys()})
        major_count = len(MAJOR_DATA)
        majors_with_satisfaction = sum(1 for m in MAJOR_DATA.values() 
                                    if m.overall_satisfaction is not None)
        
        logger.info(f"""
数据验证结果:
- 学校总数: {school_count}
  - 有满意度数据的学校数: {schools_with_satisfaction}
  - 有就业率数据的学校数: {schools_with_employment}
- 专业总数: {major_count} (来自 {unique_schools} 所学校)
  - 有满意度数据的专业数: {majors_with_satisfaction}
        """)
        
    except Exception as e:
        logger.error(f"验证数据时出错: {str(e)}")

# 初始化数据
init_data()
# 验证数据完整性
validate_data() 