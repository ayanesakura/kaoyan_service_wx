import requests
#获取token

def get_access_token():
    app_id = "wx81019c53b1467685"
    app_secret = "388ad5421609c7cdf0233702d85798d5"
    response = requests.get(f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={app_id}&secret={app_secret}',)
    access_token = response.json()['access_token']
    return access_token


