import json
import os
from loguru import logger

# 全局变量存储数据
SCHOOL_DATAS = []  # rich_fx_flat_v2.json
MAJOR_DATA = []   # fx_flat.json
CITY_DATA = {}    # city_2_province.txt
EMPLOYMENT_DATA = {}  # aggregated_employment_data.jsonl
CITY_LEVEL_MAP = city_level_map = {
    '211': set(),
    '985': set(),
    'c9': set(['北京大学', '清华大学', '复旦大学', '上海交通大学', '浙江大学', '南京大学', '中国科学技术大学', '哈尔滨工业大学', '西安交通大学'])
}

# 添加标志位标识是否已加载数据
_DATA_LOADED = False

def loads_json(path):
    """读取jsonl格式文件"""
    ds = []
    with open(path, encoding='utf-8') as f:
        for line in f.readlines():
            d = json.loads(line)
            ds.append(d)
    return ds

def load_all_data():
    """加载所有数据文件"""
    global SCHOOL_DATAS, MAJOR_DATA, CITY_DATA, EMPLOYMENT_DATA, CITY_LEVEL_MAP, _DATA_LOADED
    
    # 如果数据已加载,直接返回
    if _DATA_LOADED:
        return
    
    # 获取resources目录路径
    cur_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    resources_dir = os.path.join(cur_dir, 'resources')
    
    # 加载学校数据
    school_data_path = os.path.join(resources_dir, 'rich_fx_flat_v2.json')
    SCHOOL_DATAS = loads_json(school_data_path)
    logger.info(f"加载了 {len(SCHOOL_DATAS)} 条学校数据")
    
    # 加载专业数据
    major_data_path = os.path.join(resources_dir, 'fx_flat.json')
    MAJOR_DATA = loads_json(major_data_path)
    logger.info(f"加载了 {len(MAJOR_DATA)} 条专业数据")
    
    # 加载城市数据
    city_data_path = os.path.join(resources_dir, 'city_2_province.txt')
    with open(city_data_path, 'r', encoding='utf-8') as f:
        for line in f:
            city, province = line.strip().split('\t')
            CITY_DATA[city] = province
    logger.info(f"加载了 {len(CITY_DATA)} 条城市数据")
    
    # 加载就业数据
    employment_data_path = os.path.join(resources_dir, 'aggregated_employment_data.jsonl')
    with open(employment_data_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
                EMPLOYMENT_DATA[data['school_name']] = data['years_data']
            except json.JSONDecodeError as e:
                logger.error(f"解析就业数据行时出错: {str(e)}")
                continue
    logger.info(f"加载了 {len(EMPLOYMENT_DATA)} 所学校的就业数据")

    for data in SCHOOL_DATAS:
        school_name, is_985, is_211 = data['school_name'], data['is_985'], data['is_211']
        if is_985 == "1":
            CITY_LEVEL_MAP['985'].add(school_name)
        if is_211 == "1":
            CITY_LEVEL_MAP['211'].add(school_name)
            
    # 标记数据已加载
    _DATA_LOADED = True

load_all_data()