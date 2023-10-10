# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from logging import getLogger, Formatter, WARN, info, error, StreamHandler
from logging.handlers import RotatingFileHandler
from os import chdir, makedirs
from os.path import dirname, abspath, isdir
from flask import Flask, request, render_template, send_from_directory, jsonify, redirect, url_for


from config.settings import *
from libs.defs import parser, calls_mod, sec_to_hours, check_answer, read_cdr, parser_sum_info

# Меняем путь
chdir(dirname(abspath(__file__)))

# creates a Flask application, named app
app = Flask(__name__)


# Инициализация логов
def log_setup():
    if not isdir('logs'):
        makedirs('logs')
    # getLogger('apscheduler.executors.default').propagate = False
    log_handler = RotatingFileHandler(dirname(abspath(__file__)) + '/logs/asterisk_call_parser.log', maxBytes=1024000,
                                      backupCount=5)
    formatter = Formatter('%(asctime)s %(filename)s->%(funcName)s():%(lineno)s %(levelname)s:%(message)s')
    # formatter.converter = time.gmtime  # if you want UTC time
    log_handler.setFormatter(formatter)
    logger = getLogger()
    logger.addHandler(log_handler)

    console_handler = StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.setLevel(WARN)


# Главная страница
@app.route("/")
def root():
    call_list_for_html = parser(read_cdr('hour', dict_cursor=True))
    check_answer_list_for_html = calls_mod(check_answer(call_list_for_html, interval=CHECK_ANSWER_INTERVAL))
    call_sum_info_for_html = parser_sum_info(call_list_for_html)

    render_param = {'startdate': '',
                    'stoptdate': '',
                    'src': '',
                    'dst': '',
                    'status': '',
                    'check_answer_list_for_html': reversed(check_answer_list_for_html),
                    'call_num': call_sum_info_for_html['call_num'],
                    'sum_time_speak_wait': sec_to_hours(call_sum_info_for_html['sum_time_speak_wait']),
                    'sum_time_speak': sec_to_hours(call_sum_info_for_html['sum_time_speak']),
                    'sum_time_wait': sec_to_hours(call_sum_info_for_html['sum_time_wait']),
                    'average_time_speak_wait': sec_to_hours(call_sum_info_for_html['average_time_speak_wait']),
                    'average_time_speak': sec_to_hours(call_sum_info_for_html['average_time_speak']),
                    'average_time_wait': sec_to_hours(call_sum_info_for_html['average_time_wait']),
                    'check_answer_interval': sec_to_hours(CHECK_ANSWER_INTERVAL)
                    }
    return render_template('index.html', render_param=render_param)


# Фильтры
@app.route("/filters", methods=['post', 'get'])
def filters():
    if request.method == 'POST':
        src = request.form['src']
        dst = request.form['dst']
        status = request.form['status']

        if src != '':
            if not src.isdigit():
                src = ''
        if dst != '':
            if not dst.isdigit():
                dst = ''
        if status == 'all':
            status = ''

        startdate = request.form['startdate'].replace('T', ' ') + ':00'
        stoptdate = request.form['stoptdate'].replace('T', ' ') + ':00'

        if startdate == ':00' or stoptdate == ':00':  # Если
            call_list_for_html = parser(read_cdr('hour', dict_cursor=True), source=src, dest=dst, disp=status)
        else:
            # Меняю местами даты, если стоп меньше старта
            if datetime.strptime(startdate, "%Y-%m-%d %H:%M:%S") > datetime.strptime(stoptdate, "%Y-%m-%d %H:%M:%S"):
                startdate = request.form['stoptdate'].replace('T', ' ') + ':00'
                stoptdate = request.form['startdate'].replace('T', ' ') + ':00'

            call_list_for_html = parser(read_cdr(startdate + '*' + stoptdate), source=src, dest=dst, disp=status)

        check_answer_list_for_html = calls_mod(check_answer(call_list_for_html, interval=CHECK_ANSWER_INTERVAL))
        call_sum_info_for_html = parser_sum_info(call_list_for_html)
        startdate = request.form['startdate'].replace(' ', 'T')
        stoptdate = request.form['stoptdate'].replace(' ', 'T')
        render_param = {'startdate': startdate,
                        'stoptdate': stoptdate,
                        'src': src,
                        'dst': dst,
                        'status': status,
                        'check_answer_list_for_html': reversed(check_answer_list_for_html),
                        'call_num': call_sum_info_for_html['call_num'],
                        'sum_time_speak_wait': sec_to_hours(call_sum_info_for_html['sum_time_speak_wait']),
                        'sum_time_speak': sec_to_hours(call_sum_info_for_html['sum_time_speak']),
                        'sum_time_wait': sec_to_hours(call_sum_info_for_html['sum_time_wait']),
                        'average_time_speak_wait': sec_to_hours(call_sum_info_for_html['average_time_speak_wait']),
                        'average_time_speak': sec_to_hours(call_sum_info_for_html['average_time_speak']),
                        'average_time_wait': sec_to_hours(call_sum_info_for_html['average_time_wait']),
                        'check_answer_interval': sec_to_hours(CHECK_ANSWER_INTERVAL)
                        }
        return render_template('index.html', render_param=render_param)
    else:
        redirect(url_for('/'))


# Выбор шаблона
@app.route("/filters_tmpl", methods=['post', 'get'])
def filters_tmpl():
    startdate = ''
    stoptdate = ''
    src = ''
    dst = ''
    status = ''
    tmpl = 'hour'
    if request.method == 'POST':
        tmpl = request.form['tmpl']
    call_list_for_html = parser(read_cdr(tmpl))
    check_answer_list_for_html = calls_mod(check_answer(call_list_for_html,
                                                        interval=CHECK_ANSWER_INTERVAL))
    call_sum_info_for_html = parser_sum_info(call_list_for_html)

    render_param = {'startdate': startdate,
                    'stoptdate': stoptdate,
                    'src': src,
                    'dst': dst,
                    'status': status,
                    'check_answer_list_for_html': reversed(check_answer_list_for_html),
                    'call_num': call_sum_info_for_html['call_num'],
                    'sum_time_speak_wait': sec_to_hours(call_sum_info_for_html['sum_time_speak_wait']),
                    'sum_time_speak': sec_to_hours(call_sum_info_for_html['sum_time_speak']),
                    'sum_time_wait': sec_to_hours(call_sum_info_for_html['sum_time_wait']),
                    'average_time_speak_wait': sec_to_hours(call_sum_info_for_html['average_time_speak_wait']),
                    'average_time_speak': sec_to_hours(call_sum_info_for_html['average_time_speak']),
                    'average_time_wait': sec_to_hours(call_sum_info_for_html['average_time_wait']),
                    'check_answer_interval': sec_to_hours(CHECK_ANSWER_INTERVAL)
                    }

    return render_template('index.html', render_param=render_param)


@app.route('/audio/<path:filename>', methods=['GET'])
def play_audio(filename):
    file_audio_lst = filename.split('-')
    directory = PATH_TO_ASTERISK_MONITOR + file_audio_lst[3][:-4] + '/' \
                + file_audio_lst[3][4:-2] + '/' \
                + file_audio_lst[3][6:] + '/'
    return send_from_directory(directory, filename)


@app.route('/download/<path:filename>')
def download_audio(filename):
    # external-909-380956505142-20210304-111718-1614856638.27303.wav
    file_audio_lst = filename.split('-')
    directory = PATH_TO_ASTERISK_MONITOR + file_audio_lst[3][:-4] + '/' \
                + file_audio_lst[3][4:-2] + '/' \
                + file_audio_lst[3][6:] + '/'
    return send_from_directory(directory, filename)


# Выдаю данные таблицы cdr за указанный период
# Задать инервал "%Y-%m-%d %H:%M:%S*%Y-%m-%d %H:%M:%S"
@app.route('/read_cdr/', methods=['post', 'get'])
def show_cdr():
    if request.method == 'POST':
        interval = 'hour'
        request_data = request.get_json()

        try:
            interval = request_data['interval']
        except BaseException as e:
            print(f'{e}')

        rows = read_cdr(interval, dict_cursor=True)

        return jsonify(rows)
    return 'hello'


if __name__ == '__main__':
    log_setup()
    app.run(host=FLASK_ADDRESS, port=FLASK_PORT, debug=False)
