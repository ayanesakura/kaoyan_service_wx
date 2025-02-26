from wxcloudrun.score_card.system_employment_score_calculator import SystemEmploymentScoreCalculator
from wxcloudrun.score_card.non_system_employment_score_calculator import NonSystemEmploymentScoreCalculator
from wxcloudrun.score_card.advanced_study_score_calculator import (
    AdvancedStudyScoreCalculator, 
    EMPLOYMENT_DATA, 
    init_default_values,
    DEFAULT_VALUES
)
from wxcloudrun.score_card.location_score_calculator import LocationScoreCalculator
from wxcloudrun.score_card.major_score_calculator import MajorScoreCalculator
from wxcloudrun.score_card.admission_score_calculator import AdmissionScoreCalculator
from wxcloudrun.beans.input_models import UserInfo, TargetInfo, SchoolInfo, Area
from wxcloudrun.utils.file_util import CITY_LEVEL_MAP, SCHOOL_DATAS
from typing import Tuple, Optional, Dict
from loguru import logger
import json

def load_employment_data():
    """加载就业数据"""
    global EMPLOYMENT_DATA
    try:
        with open('wxcloudrun/resources/aggregated_employment_data.jsonl', 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                EMPLOYMENT_DATA[data['school_name']] = data['years_data']
        logger.info(f"成功加载 {len(EMPLOYMENT_DATA)} 所学校的就业数据")
    except Exception as e:
        logger.error(f"加载就业数据失败: {str(e)}")
        raise

def init_all_score_cards():
    """初始化所有评分卡"""
    # 加载就业数据
    if not EMPLOYMENT_DATA:
        load_employment_data()
        
    # 初始化升学深造评分卡
    if not DEFAULT_VALUES:
        init_default_values(EMPLOYMENT_DATA)
        logger.info("成功初始化升学深造评分卡默认值")

def get_school_info_from_data(school_name: str) -> Dict:
    """从SCHOOL_DATAS中获取学校信息"""
    for school in SCHOOL_DATAS:
        if school.get('school_name') == school_name:
            return school
    raise ValueError(f"未找到学校 {school_name} 的信息")

def get_school_level_from_map(school_name: str) -> Tuple[str, str]:
    """从CITY_LEVEL_MAP获取学校层级"""
    is_985 = "1" if (school_name in CITY_LEVEL_MAP.get('985', set()) or 
                     school_name in CITY_LEVEL_MAP.get('c9', set())) else "0"
    is_211 = "1" if (school_name in CITY_LEVEL_MAP.get('211', set()) or 
                     school_name in CITY_LEVEL_MAP.get('985', set()) or 
                     school_name in CITY_LEVEL_MAP.get('c9', set())) else "0"
    return is_985, is_211

def test_all_score_cards(school_name: str):
    """测试所有评分卡"""
    # 确保所有评分卡已初始化
    init_all_score_cards()
    
    # 获取学校实际信息
    school_data = get_school_info_from_data(school_name)
        
    # 创建测试用的用户信息
    user_info = UserInfo(
        signature="测试用户",
        gender="男",
        school=school_name,
        major=school_data.get('major', '计算机科学与技术'),
        grade="大四",
        rank="10%",
        cet="六级",
        hometown=Area(province=school_data.get('province', '北京'), 
                     city=school_data.get('city', '北京')),
        is_first_time="是"
    )
    
    # 创建测试用的目标信息
    target_info = TargetInfo(
        school_cities=[Area(province=school_data.get('province', '北京'), 
                          city=school_data.get('city', '北京'))],
        majors=[school_data.get('major', '计算机科学与技术')],
        levels=["985"],
        work_cities=[Area(province=school_data.get('province', '北京'), 
                        city=school_data.get('city', '北京'))],
        weights=[],
        directions=[]
    )
    
    # 获取学校层级
    is_985, is_211 = get_school_level_from_map(school_name)
    
    # 创建测试用的学校信息
    school_info = SchoolInfo(
        school_name=school_name,
        school_code=school_data.get('school_code', ''),
        is_985=school_data.get('is_985', '0'),
        is_211=school_data.get('is_211', '0'),
        departments=school_data.get('departments', ''),
        major=school_data.get('major', ''),
        major_code=school_data.get('major_code', ''),
        blb=school_data.get('blb', []),
        fsx=school_data.get('fsx', []),
        directions=school_data.get('directions', []),
        province=school_data.get('province', ''),
        city=school_data.get('city', '')
    )
    
    # 初始化所有评分计算器
    system_emp_calculator = SystemEmploymentScoreCalculator(user_info, target_info)
    non_system_emp_calculator = NonSystemEmploymentScoreCalculator(user_info, target_info)
    advanced_study_calculator = AdvancedStudyScoreCalculator(user_info, target_info)
    location_calculator = LocationScoreCalculator(user_info, target_info)
    major_calculator = MajorScoreCalculator(user_info, target_info)
    admission_calculator = AdmissionScoreCalculator(user_info, target_info)
    
    # 获取就业数据
    employment_data = EMPLOYMENT_DATA.get(school_name, [])
    
    # 计算所有评分
    scores = {
        '体制内就业': system_emp_calculator.calculate_total_score(school_info),
        '非体制就业': non_system_emp_calculator.calculate_total_score(school_info),
        '升学深造': advanced_study_calculator.calculate_total_score(
            school_info, 
            employment_data
        ),
        '地理位置': location_calculator.calculate_total_score(school_info),
        '专业实力': major_calculator.calculate_total_score(school_info),
        '录取概率': admission_calculator.calculate(school_info)
    }
    
    # 打印结果
    print(f"\n{school_name}的评分结果:")
    for card_name, score_result in scores.items():
        print(f"\n{'-'*20} {card_name} {'-'*20}")
        
        if card_name == '录取概率':
            # 录取概率评分卡格式不同，单独处理
            print(f"总分: {score_result.get('总分', 0):.2f}")
            for key, value in score_result.items():
                if key != '总分':
                    print(f"{key}: {value}")
        else:
            # 处理其他评分卡
            print(f"总分: {score_result['total_score']:.2f}")
            if 'dimension_scores' in score_result:
                print("\n维度得分:")
                for dimension in score_result['dimension_scores']:
                    print(f"\n{dimension['name']}:")
                    print(f"  得分: {dimension['score']:.2f}")
                    print(f"  权重: {dimension['weight']}")
                    print(f"  加权得分: {dimension['weighted_score']:.2f}")
                    print(f"  数据来源: {dimension['source']}")
                    print(f"  原始值: {dimension.get('raw_value', 'N/A')}")
                    if 'description' in dimension:
                        print(f"  描述: {dimension['description']}")
    
    return scores

if __name__ == "__main__":
    # 初始化所有评分卡
    init_all_score_cards()
    
    # 测试学校
    schools = [
        "北京大学"
    ]
    
    for school in schools:
        test_all_score_cards(school)
        print("\n" + "="*50 + "\n") 