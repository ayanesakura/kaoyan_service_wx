import os
import sys
sys.path.append(os.getcwd())
from werkzeug.utils import secure_filename
from flask import request, jsonify
from typing import List, Dict
from wxcloudrun.utils.deepseek_api_utils import DeepSeekApiClient, DeepSeekApiModel
import logging
import traceback


deepseek_client = DeepSeekApiClient(
    model=DeepSeekApiModel.MODEL_CHAT,
    timeout=60  # 60秒超时
)

logger = logging.getLogger(__name__)

def ai_ana():
    try:
        request_data = request.get_json()
        logger.info("收到请求数据")
        
        user_info = request_data.get('user_info', {})
        target_info = request_data.get('target_info', {})
        sort_info = request_data.get('sort_info', [])
        logger.info(f"用户信息: {user_info}")
        logger.info(f"目标信息: {target_info}")
        
        sort_info.sort(key=lambda x: -x['weight'])
        sort_str = '' if len(sort_info) == 0 else '、'.join([info['name'] for info in sort_info])
        
        prompt = [
            '## 角色',
            '你是一个资深的考研择校咨询师，你擅长发现学生的特点，结合他们的需求，给出合适的择校建议',
            '## 学生基本信息',
            f'学校：{user_info.get("school", "")}',
            f'专业：{user_info.get("major", "")}',
            f'年级：{user_info.get("grade", "")}',
            f'当前专业排名：{user_info.get("rank", "")}',
            f'是否一战：{user_info.get("is_first_time", "")}',
            f'擅长的科目：{user_info.get("good_subject", "")}',
            '## 目标院校信息',
            f'专业：{target_info.get("major", "")}',
            f'期望城市：{target_info.get("city", "")}',
            f'学校要求：{target_info.get("school_level", "")}',
            f'择校优先级：{sort_str}'
        ]
        prompt = '\n'.join(prompt)
        
        max_retry_times, idx = 3, 0
        while idx < max_retry_times:
            try:
                logger.info(f"尝试调用 DeepSeek API (第{idx + 1}次)")
                response = deepseek_client.run_deepseek_api(prompt, temperature=0.7)
                logger.info("DeepSeek API 调用成功")
                break
            except Exception as e:
                logger.error(f"第{idx + 1}次调用失败: {str(e)}")
                logger.error(traceback.format_exc())
                idx += 1
                if idx == max_retry_times:
                    logger.error("已达到最大重试次数")
                    return jsonify({
                        'code': 500,
                        'message': '服务暂时不可用，请稍后重试'
                    })

        return jsonify({
            'code': 200,
            'data': {
                'content': response
            }
        })
        
    except Exception as e:
        logger.error(f"处理请求失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        })


