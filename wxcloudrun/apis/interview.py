from wxcloudrun.utils.doubao import client
import requests
from werkzeug.utils import secure_filename
import os
import uuid
from flask import request, jsonify
import base64
import tempfile


def get_question():
    data = request.json
    resume = data.get('resume', '')
    questions = data.get('questions', [])
    answers = data.get('answers', [])

    # 构建提示词
    prompt = f"你是一位专业的面试官。根据以下简历信息进行面试:\n\n{resume}\n\n"
    
    if questions:
        prompt += "之前的问题和回答:\n"
        for q, a in zip(questions, answers):
            prompt += f"问: {q}\n答: {a}\n"
    
    prompt += "\n请根据简历和之前的对话(如果有),生成下一个合适的面试问题。"

    # 调用豆包API
    completion = client.chat.completions.create(
    model="ep-20241008143931-s48cx",
    messages = [
        {"role": "system", "content": "你是豆包，是由字节跳动开发的 AI 人工智能助手"},
        {"role": "user", "content": prompt},
    ],
        )
    question = completion.choices[0].message.content

    return jsonify({"success": True, "question": question})


def get_asr(base64_audio):
    url = 'http://api-audio-bj.fengkongcloud.com/audiomessage/v4'
    data =   {"accessKey": "qF8h6lEGjZKxUL8rEtA3",
        "appId": "audio_asr",
        "eventId": "game_asr",
        "type": "POLITY",
        "btId": "ayane_test_2",
        "contentType": "RAW",
        "content": base64_audio,
        "data": {
                "returnAllText":1,
                "formatInfo": "mp3"
            }
    }
    response = requests.post(url, json=data)
    return response.json()
    
def process_audio(app):
    try:
        # 获取前端发送的base64编码的音频数据
        audio_base64 = request.json.get('audio')
        # app.logger.info(f"audio_base64: {audio_base64}")
        
        if not audio_base64:
            return jsonify({'success': False, 'error': 'No audio data received'}), 400

        # 解码base64数据
        asr = get_asr(audio_base64)
        app.logger.info(f"asr: {asr}")
        asr_text = asr['detail']['audioText']
        app.logger.info(f"asr_text: {asr_text}")

        # 返回识别结果
        return jsonify({
            'success': True,
            'transcription': asr_text
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


