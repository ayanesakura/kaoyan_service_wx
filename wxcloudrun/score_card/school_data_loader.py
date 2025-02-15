import json
import os
from typing import Dict, Any
from loguru import logger

def load_school_data() -> Dict[str, Dict[str, Any]]:
    """
    加载学校专业数据
    :return: 学校专业数据字典，格式为 {学校名-专业名: 数据}
    """
    try:
        file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'resources', 
            'merged_school_data.jsonl'
        )
        logger.info(f"开始加载学校专业数据: {file_path}")
        
        school_data = {}
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                key = f"{data['school_name']}-{data['major_name']}"
                school_data[key] = data
        
        logger.info(f"成功加载 {len(school_data)} 条学校专业数据")
        return school_data
    except Exception as e:
        logger.error(f"加载学校专业数据失败: {str(e)}")
        logger.exception(e)
        return {}

# 全局变量存储学校专业数据
SCHOOL_DATA = load_school_data() 