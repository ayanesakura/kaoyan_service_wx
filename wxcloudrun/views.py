from datetime import datetime
from flask import render_template, request, jsonify
from wxcloudrun import app
from wxcloudrun.dao import delete_counterbyid, query_counterbyid, insert_counter, update_counterbyid
from wxcloudrun.model import Counters
from wxcloudrun.response import make_succ_empty_response, make_succ_response, make_err_response
from flask import request
from wxcloudrun.apis.school_search import get_school_structure, search_schools
from wxcloudrun.apis.analysis import analyze_application
from wxcloudrun.apis.query_school_majors_or_fxs import query_school_majors_or_fxs
from wxcloudrun.apis.query_majors_or_fxs import query_majors_or_fxs
from wxcloudrun.apis.query_city import query_city
from wxcloudrun.apis.choose_schools import choose_schools
from wxcloudrun.apis.ai_ana import ai_ana
from wxcloudrun.apis.kyys import kyys
from wxcloudrun.apis.choose_school_v2 import choose_schools_v2
from wxcloudrun.apis.get_school_detail import get_school_detail

@app.route('/')
def index():
    """
    :return: 返回index页面
    """
    return render_template('index.html')


@app.route('/api/count', methods=['POST'])
def count():
    """
    :return:计数结果/清除结果
    """

    # 获取请求体参数
    params = request.get_json()

    # 检查action参数
    if 'action' not in params:
        return make_err_response('缺少action参数')

    # 按照不同的action的值，进行不同的操作
    action = params['action']

    # 执行自增操作
    if action == 'inc':
        counter = query_counterbyid(1)
        if counter is None:
            counter = Counters()
            counter.id = 1
            counter.count = 1
            counter.created_at = datetime.now()
            counter.updated_at = datetime.now()
            insert_counter(counter)
        else:
            counter.id = 1
            counter.count += 1
            counter.updated_at = datetime.now()
            update_counterbyid(counter)
        return make_succ_response(counter.count)

    # 执行清0操作
    elif action == 'clear':
        delete_counterbyid(1)
        return make_succ_empty_response()

    # action参数错误
    else:
        return make_err_response('action参数错误')


@app.route('/api/count', methods=['GET'])
def get_count():
    """
    :return: 计数的值
    """
    counter = Counters.query.filter(Counters.id == 1).first()
    return make_succ_response(0) if counter is None else make_succ_response(counter.count)

@app.route('/api/school_search', methods=['POST'])
def search_schools_api():
    return search_schools()

@app.route('/api/school_structure', methods=['POST'])
def get_school_structure_api():
    return get_school_structure()

@app.route('/api/analyze', methods=['POST'])
def analyze_application_api():
    return analyze_application()

@app.route('/api/query_school_majors_or_fxs', methods=['POST'])
def query_school_majors_or_fxs_api():
    return query_school_majors_or_fxs()

@app.route('/api/query_majors_or_fxs', methods=['POST'])
def query_majors_or_fxs_api():
    return query_majors_or_fxs()


@app.route('/api/query_city', methods=['POST'])
def query_city_api():
    return query_city()

@app.route('/api/choose_schools', methods=['POST'])
def choose_schools_api():
    return choose_schools()

@app.route('/api/choose_schools_v2', methods=['POST'])
def choose_schools_v2_api():
    return choose_schools_v2()

@app.route('/api/ai_ana', methods=['POST'])
def ai_ana_api():
    return ai_ana()

@app.route('/api/kyys', methods=['POST'])
def kyys_api():
    return kyys()

@app.route('/api/get_school_detail', methods=['POST'])
def get_school_detail_api():
    return get_school_detail()
