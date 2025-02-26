import os
import sys
sys.path.append(os.getcwd())
from werkzeug.utils import secure_filename
from flask import request, jsonify
from typing import List, Dict, Any
from wxcloudrun.utils.kimi_api_utils import KimiApiClient
from datetime import datetime
import json
import logging
import re
from loguru import logger
from wxcloudrun.utils.huoshan_api_utils import DoubanAPI, DoubanApiModel

kimi_client = KimiApiClient()
huoshan_api = DoubanAPI(model=DoubanApiModel.MODEL_DEEPSEEK_R1)

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_json_string(s: str) -> str:
    """清理JSON字符串，处理常见的格式问题"""
    # 移除BOM和其他特殊字符
    s = s.encode('utf-8').decode('utf-8-sig')
    
    # 替换全角字符
    char_pairs = [
        ('，', ','), ('：', ':'), ('"', '"'), ('"', '"'),
        ('【', '['), ('】', ']'), ('｛', '{'), ('｝', '}'),
        ('；', ';'), ('！', '!'), ('（', '('), ('）', ')'),
        (' ', ' '), ('	', ' ')  # 替换特殊空格和tab
    ]
    for old, new in char_pairs:
        s = s.replace(old, new)
    
    # 使用正则表达式提取JSON部分
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    match = re.search(json_pattern, s)
    if match:
        s = match.group(0)
    
    # 处理多余的逗号
    s = re.sub(r',\s*([\]}])', r'\1', s)
    
    # 处理多余的空白字符
    s = re.sub(r'\s+', ' ', s)
    s = s.strip()
    
    return s

def get_kyys_response(school_name: str, major_name: str, user_info: Dict) -> Dict[str, Any]:
    """获取考研优势分析"""
    try:
        # 初始化火山API，使用deepseek r1模型
        api = huoshan_api
        
        # 构建prompt
        prompt = f"""请分析{user_info['school']}的学生报考{school_name}{major_name}的优势和劣势。

学生信息:
- 本科学校: {user_info['school']}
- 本科专业: {user_info['major']}
- 本科成绩排名: {user_info['rank']}
- 英语水平: {user_info['cet']}

请从以下几个方面进行分析:
1. 学校层次跨度分析
2. 专业匹配度分析
3. 竞争优势分析
4. 需要重点提升的方面

请用简洁的语言直接给出分析结果，不要有多余的开场白和结束语。每个方面的分析控制在2-3句话以内。"""

        # 构建消息
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        # 调用API
        response = api.chat_completion(
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        return {
            "code": 0,
            "data": response
        }
        
    except Exception as e:
        logger.error(f"获取考研优势分析失败: {str(e)}")
        logger.exception("详细错误信息:")
        return {
            "code": 500,
            "message": f"获取考研优势分析失败: {str(e)}"
        }

def kyys():
    request_data = request.get_json()
    birthday = request_data.get('birthday', '')
    mbti = request_data.get('mbti', '')
    signature = request_data.get('signature', '')
    gender = request_data.get('gender', '')
    if not birthday or not signature or not gender:
        return jsonify({
            'code': 400,
            'message': '生日、性别和个性签名不能为空'
        })


    prompt = f"""
## 角色
你是一位幽默风趣、又对考研形势有着深刻洞察的"神秘运势预言家"。你的目标是给每日努力备考的学生提供趣味性、实用性指引，让他们在紧张的备考之余，也能在日常生活中找到乐趣和自我调剂的方式。

## 任务1：考研运势
- 复习效率指数：今天复习、做题的专注度和高效度如何？
- 刷题顺利度：今天的刷题体验是否丝滑？遇到难题的概率大不大？会不会频繁卡壳？
- 抢座运势：今天去自习室或图书馆能不能抢到一个风水宝座？是否会因为座位紧缺而耽误复习？
- 意外惊喜指数：今天会不会在复习之外收获一些小确幸？比如遇到名师开直播、老师划重点、领取补助、或者在图书馆偶遇"心仪学长/学姐"？
内容要求：请对这四项指数分别给出一个数值（0-100）

## 任务2：今日宜、今日不宜
今日宜：从考研复习、日常生活、情绪管理等角度，结合考研场景，给出 1-3 条具体、可执行的"宜做"事项，并以幽默有趣的方式阐述。
今日忌：从可避免的坏习惯、错误思维或浪费时间的行为等方面，结合考研特征，给出 1-3 条"不宜做"事项，并用轻松调侃的口吻提醒学生注意。
风格要求：文字要带有一定的幽默感和考研属性，让学生在阅读后会心一笑，但同时能获得切实的备考建议。
要求：简短（不超过5个字），有趣

## 任务3：今日幸运色、今日幸运数字、今日幸运方向，今日幸运食物
今日幸运色：给出幸运色和颜色编码
今日幸运数字：给出幸运数字
今日幸运方向：给出幸运方向
今日幸运食物：给出幸运食物

## 任务4：总结任务1-3
一段简短幽默的话总结任务1-3

请严格以JSON的格式输出，不要有多余的文字

""" + """
{"颜色编码": "#000000", "复习效率指数": 80, "刷题顺利度": 79, "抢座运势": 89, "意外惊喜指数": 88, "今日宜": ["建议1"， ...], "今日忌": ["建议1"， ...], "今日幸运色": "黑色", "今日幸运方向": "东北", "今日幸运数字": 7, "今日幸运食物": "小龙虾", "总结": "任务1-3的总结"}
"""

    max_retry_times, idx = 3, 0
    data_dict = {'code': 500, 'message': '服务暂时不可用,请稍后重试'}
    
    while idx < max_retry_times:
        try:
            response = huoshan_api.chat_completion(messages=[{"role": "user", "content": prompt}])
            # 记录原始响应
            logger.info(f"Original Huoshan API Response: {response}")
            
            # 清理和预处理JSON字符串
            cleaned_response = clean_json_string(response)
            logger.info(f"Cleaned Response: {cleaned_response}")
            
            # 尝试解析JSON
            data_dict = json.loads(cleaned_response)
            
            # 验证必要的字段是否存在
            required_fields = ['复习效率指数', '刷题顺利度', '抢座运势', '意外惊喜指数', '今日宜', '今日忌', '今日幸运色', '今日幸运方向', '今日幸运数字', '今日幸运食物', '总结']
            if not all(field in data_dict for field in required_fields):
                raise ValueError("Missing required fields in response")
                
            data_dict['code'] = 200
            break
            
        except json.JSONDecodeError as je:
            logger.error(f"JSON解析错误: {str(je)}")
            logger.error(f"问题字符串: {cleaned_response}")
            idx += 1
            if idx == max_retry_times:
                data_dict = {
                    'code': 500,
                    'message': 'JSON解析失败,请稍后重试',
                    'error': str(je)
                }
        except ValueError as ve:
            logger.error(f"数据验证错误: {str(ve)}")
            idx += 1
            if idx == max_retry_times:
                data_dict = {
                    'code': 500,
                    'message': '返回数据格式不完整,请稍后重试',
                    'error': str(ve)
                }
        except Exception as e:
            logger.error(f"其他错误: {str(e)}")
            idx += 1
            if idx == max_retry_times:
                data_dict = {
                    'code': 500,
                    'message': '服务异常,请稍后重试',
                    'error': str(e)
                }
    
    return jsonify(data_dict)
