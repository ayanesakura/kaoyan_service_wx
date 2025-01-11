import requests
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
from wxcloudrun.utils.file_util import load_pdf
import os
from wxcloudrun.utils.file_util import download_file_from_wxcloud

    
def analyze_text(client, text):
    completion = client.chat.completions.create(
    model="ep-20241008143931-s48cx",
    messages = [
        {"role": "system", "content": "你是豆包，是由字节跳动开发的 AI 人工智能助手"},
        {"role": "user", "content": "这是我的简历，请帮我对简历进行评分，评分维度可以是详细程度、有无亮点等"},
        {"role": "user", "content": f"简历内容：\n{text}"},
    ],
        )
    return completion.choices[0].message.content

def analyze_resume(save_dir):
    data = request.json
    if not data or 'fileId' not in data:
        return jsonify({'success': False, 'error': '缺少文件ID'}), 400

    file_id = data['fileId']
    
    try:
        # 提取PDF文本
        file_path = download_file_from_wxcloud(file_id, save_dir)
        resume_text = load_pdf(file_path)
        
        # 调用豆包API进行分析
        # analysis_result = analyze_text(resume_text)
        analysis_result = 'None'
        
        # 假设analyze_text函数返回一个包含summary, skills, experience和education的字典
        return jsonify({
            'success': True,
            'summary': analysis_result,
            'resume': resume_text
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500