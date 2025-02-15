import json
import os
from typing import Dict, Any
from loguru import logger

def load_city_scores() -> Dict[str, Dict[str, Any]]:
    """
    加载城市评分数据
    :return: 城市评分数据字典，格式为 {城市名: 城市数据}
    """
    try:
        file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'resources', 
            'city_scores.json'
        )
        logger.info(f"开始加载城市评分数据: {file_path}")
        
        city_scores = {}
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                city_scores[data['城市']] = {
                    '原始数据': data['原始数据'],
                    '分位点得分': data['分位点得分'],
                    '总分': data['总分']
                }
        
        logger.info(f"成功加载 {len(city_scores)} 个城市的评分数据")
        return city_scores
    except Exception as e:
        logger.error(f"加载城市评分数据失败: {str(e)}")
        logger.exception(e)
        return {}

# 全局变量存储城市数据
CITY_SCORES = load_city_scores() 