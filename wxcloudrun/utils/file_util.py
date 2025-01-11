import PyPDF2
from wxcloudrun.utils import get_access_token
import requests
import os


def load_pdf(pdf_path):
    # 读取PDF文件
    texts = []
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            texts.append(page.extract_text())
    return '\n'.join(texts)


def download_file_from_wxcloud(file_id, save_dir):
    env_id = 'prod-0g0dkv502d54c928'
    access_token = get_access_token()
    url = f'https://api.weixin.qq.com/tcb/batchdownloadfile?access_token={access_token}'
    data = {
        "env": env_id,
        "file_list": [{"fileid": file_id, "max_age": 7200}]
    }
    response = requests.post(url, json=data)
    res = response.json()
    download_url = res['file_list'][0]['download_url']
    response = requests.get(download_url)
    file_name = file_id.split('/')[-1]
    with open(os.path.join(save_dir, file_name), 'wb') as f:
        f.write(response.content)
    return os.path.join(save_dir, file_name)