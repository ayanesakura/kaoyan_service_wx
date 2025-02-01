import os
import sys
sys.path.append(os.getcwd())
from werkzeug.utils import secure_filename
from wxcloudrun.utils.file_util import loads_json
from flask import request, jsonify
from typing import List, Dict
from wxcloudrun.utils.kimi_api_utils import KimiApiClient
from datetime import datetime
import json
import logging
import re

kimi_client = KimiApiClient()

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

    # 解析生日获取年龄
    birth_date = datetime.strptime(birthday, '%Y-%m-%d')
    today = datetime.now()
    age = today.year - birth_date.year
    if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
        age -= 1

    # 解析星座
    month = birth_date.month
    day = birth_date.day
    
    constellation = ''
    if (month == 3 and day >= 21) or (month == 4 and day <= 19):
        constellation = '白羊座'
    elif (month == 4 and day >= 20) or (month == 5 and day <= 20):
        constellation = '金牛座'
    elif (month == 5 and day >= 21) or (month == 6 and day <= 21):
        constellation = '双子座'
    elif (month == 6 and day >= 22) or (month == 7 and day <= 22):
        constellation = '巨蟹座'
    elif (month == 7 and day >= 23) or (month == 8 and day <= 22):
        constellation = '狮子座'
    elif (month == 8 and day >= 23) or (month == 9 and day <= 22):
        constellation = '处女座'
    elif (month == 9 and day >= 23) or (month == 10 and day <= 23):
        constellation = '天秤座'
    elif (month == 10 and day >= 24) or (month == 11 and day <= 22):
        constellation = '天蝎座'
    elif (month == 11 and day >= 23) or (month == 12 and day <= 21):
        constellation = '射手座'
    elif (month == 12 and day >= 22) or (month == 1 and day <= 19):
        constellation = '摩羯座'
    elif (month == 1 and day >= 20) or (month == 2 and day <= 18):
        constellation = '水瓶座'
    else:
        constellation = '双鱼座'
    
    # 获取生肖
    chinese_zodiac = ['鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊', '猴', '鸡', '狗', '猪']
    zodiac = chinese_zodiac[(birth_date.year - 1900) % 12]

    # 获取当前月份、天和星期
    weekday_map = {
        0: '星期一',
        1: '星期二', 
        2: '星期三',
        3: '星期四',
        4: '星期五',
        5: '星期六',
        6: '星期日'
    }
    current_month = today.month
    current_day = today.day
    current_weekday = weekday_map[today.weekday()]

    prompt = f"""
## 角色背景
你是一位幽默风趣、又对考研形势有着深刻洞察的"神秘运势预言家"。你的目标是给每日努力备考的学生提供趣味性、实用性指引，让他们在紧张的备考之余，也能在日常生活中找到乐趣和自我调剂的方式。

## 考研学生的个人信息
年龄：{age}岁
性别：{gender}
星座：{constellation}
mbti： {mbti}
昵称：{signature}

## 今日信息
星期：{current_weekday}
月份：{current_month}月

## 任务1：考研运势
- 复习效率指数
描述：今天复习、做题的专注度和高效度如何？是"顺风开挂"（效率爆棚）还是"逆风摸鱼"？
用法：提醒考研人是否需要合理规划时间、集中注意力，或需要额外的动力提升。
- 刷题顺利度
描述：今天的刷题体验是否丝滑？遇到难题的概率大不大？会不会频繁卡壳？
用法：对于备考阶段题海战术的同学很有参考价值，指导他们是否需要变换题型或策略。
- 抢座运势
描述：今天去自习室或图书馆能不能抢到一个风水宝座？是否会因为座位紧缺而耽误复习？
用法：给每日安排提供指导，提示是否需要早起或提前去"占领阵地"
- 意外惊喜指数
描述：今天会不会在复习之外收获一些小确幸？比如遇到名师开直播、老师划重点、领取补助、或者在图书馆偶遇"心仪学长/学姐"？
用法：作为生活调味剂，让每日运势多点期待感。

内容要求：请对这四项指数分别给出一个数值（0-100），并搭配简短的幽默描述。
风格要求：文字要带有一定的幽默感和考研属性，让学生在阅读后会心一笑，但同时能获得切实的备考建议

## 任务2：今日宜、今日不宜
今日宜：从考研复习、日常生活、情绪管理等角度，结合考研场景，给出 1-3 条具体、可执行的"宜做"事项，并以幽默有趣的方式阐述。
今日忌：从可避免的坏习惯、错误思维或浪费时间的行为等方面，结合考研特征，给出 1-3 条"不宜做"事项，并用轻松调侃的口吻提醒学生注意。
风格要求：文字要带有一定的幽默感和考研属性，让学生在阅读后会心一笑，但同时能获得切实的备考建议。
格式示例（可自行微调）：
"今日宜"使用简洁的列举或小段落说明；
"今日忌"同样以列举或小段落说明；
每条"宜"或"忌"后可附上一两句趣味说明或小提示，最好与考研相关。

## 任务2示例输出
今日宜
早起 10 分钟做 5 道数学选择题：一日之计在于晨，刷个小题让大脑快速进入考试模式。
听一首鼓舞人心的 BGM：当你想要放弃时，BGM 会提醒你去图书馆的路就在脚下。
今日忌
刷短视频超过 30 分钟：是短暂的快乐，还是考研后的快乐，更需要你来"刷"出答案。
熬夜追剧：后悔药比某些网剧还难找，下次躺平前先想想明天的高数习题吧。

## 任务3：今日幸运色、今日幸运数字、今日幸运方向
今日幸运色：与考研状态或复习心态相结合，描述为什么这个颜色能够带给他们正能量或帮助他们保持专注。
今日幸运数字：并解释其与考研复习的关联，如何能够给他们带来动力或象征什么潜在寓意。
今日幸运方向：指一个方位（如南、北等），或泛指一个复习的努力方向，解释为什么在今天特别重要。
风格要求：文字要带有一定的幽默感和考研属性，让学生在阅读后会心一笑，但同时能获得切实的备考建议。
格式示例（可自行微调）：
每条"今日幸运色"、"今日幸运数字"、"今日幸运方向"后可附上一两句趣味说明或小提示，最好与考研相关。

## 任务4：总结任务1-3
一段简短幽默的话总结任务1-3

输出格式为json，示例如下

""" + """
{"考研运势": [{"name": "复习效率指数", "score": 80, "description": "趣味说明"}, ...], "今日宜": ["建议1：趣味提示"， ...], "今日忌": ["建议1：趣味提示"， ...], "今日幸运色": {"value": "幸运色", "description": "趣味说明"}, "今日幸运方向": {"value": "幸运方向", "description": "趣味说明"}, "今日幸运数字": {"value": "幸运数字", "description": "趣味说明"}, "总结": "任务1-3的总结"}
"""

    max_retry_times, idx = 3, 0
    data_dict = {'code': 500, 'message': '服务暂时不可用,请稍后重试'}
    
    while idx < max_retry_times:
        try:
            response = kimi_client.run_kimi_api(prompt)
            # 记录原始响应
            logger.info(f"Original Kimi API Response: {response}")
            
            # 清理和预处理JSON字符串
            cleaned_response = clean_json_string(response)
            logger.info(f"Cleaned Response: {cleaned_response}")
            
            # 尝试解析JSON
            data_dict = json.loads(cleaned_response)
            
            # 验证必要的字段是否存在
            required_fields = ['考研运势', '今日宜', '今日忌', '今日幸运色', '今日幸运方向', '今日幸运数字', '总结']
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
