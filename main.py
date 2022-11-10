# -*- coding: utf-8 -*-
from contextlib import closing
from datetime import datetime, timedelta
from logging import getLogger, Formatter, WARN, info, error
from logging.handlers import RotatingFileHandler
from os import chdir, makedirs
from os.path import dirname, abspath, isdir
from flask import Flask, request, render_template, send_from_directory, jsonify, redirect, url_for
from pymysql import connect, Error
from pymysql.cursors import DictCursor

from config.settings import *

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
    formatter = Formatter('%(asctime)s %(levelname)s:%(message)s')
    # formatter.converter = time.gmtime  # if you want UTC time
    log_handler.setFormatter(formatter)
    logger = getLogger()
    logger.addHandler(log_handler)
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


# Читаю базу данных cdr
def read_cdr(interval='hour', dict_cursor=True):
    now_t = datetime.now()
    if interval == 'hour':
        time_delta = now_t - timedelta(hours=1)
    elif interval == 'day':
        time_delta = now_t - timedelta(days=1)
    elif interval == 'week':
        time_delta = now_t - timedelta(weeks=1)
    elif interval == 'month':
        time_delta = now_t - timedelta(days=30)
    elif interval == 'year':
        time_delta = now_t - timedelta(days=365)
    else:
        try:
            interval_list = interval.split('*')
            now_t = datetime.strptime(interval_list[1], "%Y-%m-%d %H:%M:%S")
            time_delta = datetime.strptime(interval_list[0], "%Y-%m-%d %H:%M:%S")

            # Если первое значение времени больше второго, то меняем местами, иначе запрос вернет пустое значение.
            if now_t < time_delta:
                now_t = datetime.strptime(interval_list[0], "%Y-%m-%d %H:%M:%S")
                time_delta = datetime.strptime(interval_list[1], "%Y-%m-%d %H:%M:%S")

        except BaseException as e:
            error(str(e))
            return None
    now = now_t.strftime("%Y-%m-%d %H:%M:%S")
    delta = time_delta.strftime("%Y-%m-%d %H:%M:%S")
    query = 'SELECT * FROM cdr WHERE calldate BETWEEN "' + delta + '" AND "' + now + '"'
    if dict_cursor:
        return query_db_dict(query)
    else:
        return query_db(query)


# Запрос к базе
def query_db(query_):
    try:
        with closing(connect(
                host=HOST,
                user=DB_USER,
                password=PASSWD,
                db=DB_NAME,
                charset='utf8mb4',
        )) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query_)
                if cursor.rowcount <= 0:
                    return None
                else:
                    rows = cursor.fetchall()
                    return rows
    except Error as e:
        error(str(e))
        return None


# Запрос к базе
def query_db_dict(query_):
    try:
        with closing(connect(
                host=HOST,
                user=DB_USER,
                password=PASSWD,
                db=DB_NAME,
                charset='utf8mb4',
        )) as connection:
            with connection.cursor(DictCursor) as cursor:
                cursor.execute(query_)
                if cursor.rowcount <= 0:
                    return None
                else:
                    rows = cursor.fetchall()
                    return rows
    except Error as e:
        error(str(e))
        return None


# Парсим строки с базы данных
def parser(rows, source='', dest='', disp=''):

    # Проверка на совпадение с фильтром
    def call_filter(call_):
        if source != '':
            if source == call_['src'] or ('38' + str(source)) == call_['src'] or \
                    ('+38' + str(source)) == call_['src']:
                return True
            else:
                return False
        elif dest != '':
            if dest == call_['dst'] or ('38' + str(dest)) == call_['dst'] or \
                    ('+38' + str(dest)) == call_['dst']:
                return True
            else:
                return False
        elif disp != '':
            if disp in (call_['disposition'], call_.get('ans_disp')):
                return True
            else:
                return False
        else:
            return True

    # Выбираю кто куда звонил
    def sel_dst_nam(call_):
        if call_['dcontext'] in ('ext-group', 'ext-queues', 'app-blackhole'):
            if call_['dstchannel'].find('SIP') != -1:
                dst_ = call_['dstchannel'][4:-9]
                src_ = call_['src']
                return {'src': src_, 'dst': dst_}
        elif call_['dcontext'] in ('followme-check', 'from-internal', 'ext-local'):
            return {'src': call_['cnum'], 'dst': call_['dst']}
        elif call_['dcontext'].find('ivr') != -1:
            dst_ = f"{call_['channel'][4:-9]} (ivr)"
            return {'src': call_['src'], 'dst': dst_}
        else:
            return {'src': call_['cnum'], 'dst': call_['dst']}

    if rows is None:
        return None

    call_list = []
    uniqueid_calls_dict = {}

    # Группировка событий по linkedid и uniqueid
    # Выбираю записи с совпадающими полями linkedid и uniqueid
    for call in rows.copy():
        uniqueid_split = call['uniqueid'].split('.')
        linkedid_split = call['linkedid'].split('.')
        if uniqueid_split[0] == linkedid_split[0]:
            if uniqueid_calls_dict.get(uniqueid_split[0]) is None:  # Если первое совпадение создаю новый ключ
                uniqueid_calls_dict.update({uniqueid_split[0]: [call]})
            else:  # Обновляю ключ добавляя поле
                exist_calls = uniqueid_calls_dict[uniqueid_split[0]]
                exist_calls.append(call)
                uniqueid_calls_dict.update({uniqueid_split[0]: exist_calls})
            rows.remove(call)

    # Разгребаю несовпадающие, отбрасываю огрызки
    for call in rows.copy():
        linkedid_split = call['linkedid'].split('.')
        if uniqueid_calls_dict.get(linkedid_split[0]) is not None:
            exist_calls = uniqueid_calls_dict[linkedid_split[0]]
            exist_calls.append(call)
            uniqueid_calls_dict.update({linkedid_split[0]: exist_calls})
            rows.remove(call)

    # Выхожу если пустой список
    if len(uniqueid_calls_dict) == 0:
        return None

    # Анализ списка звонков, выясняем статус звонка, направление, время ожидания и разговора и т. д.
    for uniqueid, uniqueid_calls_list in uniqueid_calls_dict.items():
        uniqueid_calls_list_sorted = sorted(uniqueid_calls_list, key=lambda d: d['calldate'])  # Сортирую по времени
        call_status = {'answered': False, 'position': None}
        callwait = 0
        for call in uniqueid_calls_list_sorted:
            if call['disposition'] == 'ANSWERED' and call['dcontext'] \
                    not in ('app-blackhole', 'from-internal-xfer', 'macro-dial-one', 'macro-dial'):  # Если ответили
                call_status.update({'answered': True})
                if call['dcontext'] == 'ext-queues':  # Если ответли с очереди
                    call_status.update({'position': 'queue'})
                    call_status.update({'call': call})
                elif call['channel'].find('from-queue') != -1:  # Если ответли с очереди на екстен
                    call_status.update({'position': 'from-queue'})
                    call_status.update({'call': call})
                elif call['dcontext'] == 'ext-group':
                    call_status.update({'position': 'ring_group'})
                    call_status.update({'call': call})
                else:
                    call_status.update({'call': call})
            else:
                if call['billsec'] != call['duration']:
                    callwait = callwait + call['duration']
                if not call_status['answered']:
                    call_status.update({'call': call})

        calldate = call_status['call'].get('calldate').strftime("%Y-%m-%d %H:%M:%S")
        billsec = call_status['call'].get('billsec')
        recordingfile = call_status['call'].get('recordingfile')
        context = call_status['call'].get('dcontext')
        # Если в звонок в контексте заглушки или ИВР то помечаю - не ответили
        if (call_status['call'].get('dcontext') in 'app-blackhole')\
                or call_status['call'].get('dcontext').find('ivr') != -1:
            disposition = 'NO ANSWER'
        else:
            disposition = call_status['call'].get('disposition')

        duration = call_status['call'].get('duration')
        uniqueid = call_status['call'].get('uniqueid')
        if callwait == 0:
            callwait = duration - billsec
        try:
            call_direction = sel_dst_nam(call_status.get('call'))
            src = call_direction.get('src')
            dst = call_direction.get('dst')
        except BaseException as e:
            error(str(e))
            continue

        call_list.append({'calldate': calldate,
                          'src': src,
                          'dst': dst,
                          'disposition': disposition,
                          'billsec': billsec,
                          'recordingfile': recordingfile,
                          'context': context,
                          'duration': duration,
                          'uniqueid': uniqueid,
                          'callwait': callwait
                          })

    if dest != '' or source != '' or disp != '':  # Если включен фильтр
        call_list_filtred = []
        for call in call_list:
            if call_filter(call):
                call_list_filtred.append(call)
        return call_list_filtred
    else:
        return call_list


# Парсер Сумарная информация
def parser_sum_info(call_list_):
    if call_list_ is None:
        call_num = 0
    else:
        call_num = len(call_list_)  # Количество звонков
    sum_time_speak = 0
    sum_time_wait = 0
    sum_time_speak_wait = 0
    average_time_speak = 0
    average_time_wait = 0
    average_time_speak_wait = 0
    if call_num != 0 and call_list_[0] != '':
        # Считаем время разгоровра, ожидания, и т.д.
        for call in call_list_:
            try:
                call_check = isinstance(call['billsec'], int)
                if call_check:
                    sum_time_speak = sum_time_speak + call['billsec']  # Общее время разговора
                else:
                    sum_time_speak = sum_time_speak + sum(
                        x * int(t) for x, t in zip([60, 1], call['billsec'].split(":")))
            except BaseException as e:
                info(str(e))
                sum_time_speak = sum_time_speak + 0

            sum_time_wait = sum_time_wait + (int(call['duration']) - int(call['billsec']))  # Общее время ожидания
            sum_time_speak_wait = sum_time_speak + sum_time_wait  # Общее время ожидания и разговора

        average_time_speak = sum_time_speak / call_num  # Среднее время звонка
        average_time_wait = sum_time_wait / call_num
        average_time_speak_wait = sum_time_speak_wait / call_num

    call_sum_info = {'call_num': call_num,
                     'sum_time_speak': sum_time_speak,
                     'sum_time_wait': sum_time_wait,
                     'sum_time_speak_wait': sum_time_speak_wait,
                     'average_time_speak': average_time_speak,
                     'average_time_wait': average_time_wait,
                     'average_time_speak_wait': average_time_speak_wait}
    return call_sum_info


# Проверка перезвона
def check_answer(calls, interval=900):
    if calls is None:
        return None
    if len(calls) == 0:
        return None

    calls_with_answers = []
    for call in calls:
        if call['context'] == 'from-internal':  # Отбрасываем внутренние номера
            calls_with_answers.append(call)
            continue
        if call['disposition'] == 'ANSWERED':
            calls_with_answers.append(call)
            continue
        if call['disposition'] == 'NO ANSWER':
            # Выбираем диапазон звонков в заданом интервале
            chk_call_list = list()
            # Время звонка
            call_start = datetime.strptime(call['calldate'], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")

            # Получаю дату конца поиска
            end_time_str = (datetime.strptime(call['calldate'], "%Y-%m-%d %H:%M:%S") + timedelta(
                seconds=int(interval))).strftime("%Y-%m-%d %H:%M:%S")

            # Выбираю записи за период
            interval_slice = f'{call_start}*{end_time_str}'
            calls_list_slice = parser(read_cdr(interval=interval_slice, dict_cursor=True), source=call['src'],
                                      dest=call['src'])

            # Отбираю звонки где упоминается src
            try:
                for call_in_slice in calls_list_slice:
                    call_src = shot_number(call['src'])
                    slice_disp = call_in_slice['disposition']
                    slice_src = shot_number(call_in_slice['src'])
                    slice_dst = shot_number(call_in_slice['dst'])
                    if (slice_src == call_src and slice_disp == 'ANSWERED') or (
                            slice_dst == call_src and slice_disp == 'ANSWERED'):
                        chk_call_list.append(call_in_slice)
            except BaseException as e:
                error(str(e))

            if len(chk_call_list) == 0:  # Проверяю длину списка, если пустой - не ответили или не перезвонили
                call.update({'ans_disp': 'Did not call back',
                             'ans_disp_calldate': call['calldate']}
                            )
            else:
                ans_disp = 'Did not call back'
                for chk_call in chk_call_list:
                    if chk_call['disposition'] == 'ANSWERED':
                        if call == chk_call:
                            continue
                        elif chk_call['context'] in ('ext-group', 'ext-local'):

                            if chk_call['src'] == call['src']:
                                ans_disp = 'Client call back'
                            else:
                                ans_disp = 'Call back'
                            call.update({'ans_disp': ans_disp,
                                         'ans_disp_calldate': chk_call['calldate'],
                                         'ans_src': chk_call['src'],
                                         'ans_dst': chk_call['dst']}
                                        )
                            break
                        else:
                            ans_disp = 'Call back'
                    elif chk_call['disposition'] == 'BUSY':
                        ans_disp = 'Call back but busy'
                    elif chk_call['disposition'] == 'FAILED':
                        ans_disp = 'Call back but failed'
                    else:
                        ans_disp = 'Call back no answer'

                    if ans_disp != 'Did not call back':
                        call.update({'ans_disp': ans_disp,
                                     'ans_disp_calldate': chk_call['calldate'],
                                     'ans_src': chk_call['src'],
                                     'ans_dst': chk_call['dst']}
                                    )
                        break
                else:
                    call.update({'ans_disp': ans_disp,
                             'ans_disp_calldate': call['calldate'],
                             'ans_src': call['src'],
                             'ans_dst': call['dst']}
                            )
        calls_with_answers.append(call)
    return calls_with_answers


def calls_mod(calls):
    # 0 - ANSWERED          0 - Call back
    # 1 - NO ANSWER         1 - Call back no answer
    # 2 - BUSY              2 - Call back but busy
    # 3 - FAILED            3 - Call back but failed
    #                       4 - Did not call back
    #                       5 - Client call back

    if calls is None:
        return []

    mod_calls = []
    i = 1
    for call in calls:
        # Формирую список для отображения в вебе
        mod_call = {'calldate': time_shift(call['calldate']),
                    'src': shot_number(call['src']),
                    'dst': shot_number(call['dst']),
                    'billhour': sec_to_hours(call['billsec']),
                    'durationhour': sec_to_hours(call['duration']),
                    # 'callwait': sec_to_hours(int(call['duration']) - int(call['billsec'])),
                    'callwait': sec_to_hours(call['callwait']),
                    'npp': i,
                    }
        call.update(mod_call)
        mod_calls.append(call)
        i += 1
    return mod_calls


# Корректировка отображения времени
def time_shift(date_):
    s_time = datetime.strptime(date_, "%Y-%m-%d %H:%M:%S")
    return s_time.strftime("%Y-%m-%d %H:%M:%S")


# Обрезаем 38 +38
def shot_number(number):
    if len(number) == 12:
        cat_number = number[2:]
    elif len(number) == 13:
        cat_number = number[3:]
    else:
        cat_number = number
    return cat_number


# Переводим секунды в минуты и часы
def sec_to_hours(sec):
    sec = int(sec)
    if sec < 3600:
        mod_sec = str(timedelta(seconds=sec))[2:]
    else:
        mod_sec = str(timedelta(seconds=sec))
    return mod_sec


# Удаление пустой даты
def mod_answer_date(answer_date):
    if answer_date == '0000-00-00 00:00:00':
        ans_dst = ''
    else:
        ans_dst = answer_date
    return ans_dst


def to_fixed(num_obj, digits=0):
    return f"{num_obj:.{digits}f}"


if __name__ == '__main__':
    log_setup()
    app.run(host=FLASK_ADDRESS, port=FLASK_PORT, debug=False)
