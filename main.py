# -*- coding: utf-8 -*-
from contextlib import closing
from datetime import datetime, timedelta
from logging import getLogger, Formatter, WARN, info, error
from logging.handlers import RotatingFileHandler
from os import chdir, makedirs
from os.path import dirname, abspath, isdir
from flask import Flask, request, render_template, send_from_directory
from pymysql import connect, Error
from config.settings import *

# Меняем путь
chdir(dirname(abspath(__file__)))

# creates a Flask application, named app
app = Flask(__name__)


# Инициализация логов
def log_setup():
    if not isdir('./log'):
        makedirs('./log')
    # getLogger('apscheduler.executors.default').propagate = False
    log_handler = RotatingFileHandler(dirname(abspath(__file__)) + '/log/asterisk_call_parser.log', maxBytes=1024000000,
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
    startdate = ''
    stoptdate = ''
    src = ''
    dst = ''
    status = ''
    call_list_for_html = parser(read_cdr('hour'))
    check_answer_list_for_html = calls_mod(check_answer(call_list_for_html, interval=CHECK_ANSWER_INTERVAL))
    call_sum_info_for_html = parser_sum_info(call_list_for_html)
    return render_template('index.html',
                           check_answer_list_for_html=reversed(check_answer_list_for_html),
                           call_num=call_sum_info_for_html['call_num'],
                           sum_time_speak_wait=sec_to_hours(call_sum_info_for_html['sum_time_speak_wait']),
                           sum_time_speak=sec_to_hours(call_sum_info_for_html['sum_time_speak']),
                           sum_time_wait=sec_to_hours(call_sum_info_for_html['sum_time_wait']),
                           average_time_speak_wait=sec_to_hours(call_sum_info_for_html['average_time_speak_wait']),
                           average_time_speak=sec_to_hours(call_sum_info_for_html['average_time_speak']),
                           average_time_wait=sec_to_hours(call_sum_info_for_html['average_time_wait']),
                           startdate=startdate,
                           stoptdate=stoptdate,
                           src=src,
                           dst=dst,
                           status=status)


# Фильтры
@app.route("/filters", methods=['post', 'get'])
def filters():
    src = ''
    dst = ''
    status = ''
    call_back = False
    call_back_n = False
    call_back_b = False
    call_back_f = False
    no_call_back = False
    cl_call_back = False

    if request.method == 'POST':
        src = request.form['src']
        dst = request.form['dst']
        status = request.form['status']
        call_back = request.form['status']

        if call_back == 'call back':
            call_back = True
            call_back_n = False
            call_back_b = False
            call_back_f = False
            no_call_back = False
            cl_call_back = False
            status = ''
        elif call_back == 'call back no answer':
            call_back = False
            call_back_n = True
            call_back_b = False
            call_back_f = False
            no_call_back = False
            cl_call_back = False
            status = ''
        elif call_back == 'call back but busy':
            call_back = False
            call_back_n = False
            call_back_b = True
            call_back_f = False
            no_call_back = False
            cl_call_back = False
            status = ''
        elif call_back == 'call back but fail':
            call_back = False
            call_back_n = False
            call_back_b = False
            call_back_f = True
            no_call_back = False
            cl_call_back = False
            status = ''
        elif call_back == 'no call back':
            call_back = False
            call_back_n = False
            call_back_b = False
            call_back_f = False
            no_call_back = True
            cl_call_back = False
            status = ''
        elif call_back == 'client call back':
            call_back = False
            call_back_n = False
            call_back_b = False
            call_back_f = False
            no_call_back = False
            cl_call_back = True
            status = ''
        else:
            call_back = False
            call_back_n = False
            call_back_b = False
            call_back_f = False
            no_call_back = False
            cl_call_back = False

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
            call_list_for_html = parser(read_cdr('hour'), source=src, dest=dst, disp=status)
        else:
            # Меняю местами даты, если стоп меньше старта
            if datetime.strptime(startdate, "%Y-%m-%d %H:%M:%S") > datetime.strptime(stoptdate, "%Y-%m-%d %H:%M:%S"):
                startdate = request.form['stoptdate'].replace('T', ' ') + ':00'
                stoptdate = request.form['startdate'].replace('T', ' ') + ':00'
            call_list_for_html = parser(read_cdr(startdate + '*' + stoptdate), source=src, dest=dst, disp=status)
    else:
        call_list_for_html = parser(read_cdr('hour'), source=src, dest=dst, disp=status)

    check_answer_list = check_answer(call_list_for_html, interval=CHECK_ANSWER_INTERVAL)
    check_answer_list_for_html = calls_mod(check_answer_list,
                                           call_back=call_back,
                                           call_back_n=call_back_n,
                                           call_back_b=call_back_b,
                                           call_back_f=call_back_f,
                                           no_call_back=no_call_back,
                                           cl_call_back=cl_call_back)

    call_sum_info_for_html = parser_sum_info(check_answer_list_for_html)

    # Конвертирую обратно для datetime-local
    startdate = request.form['startdate'].replace(' ', 'T')
    stoptdate = request.form['stoptdate'].replace(' ', 'T')

    return render_template('index.html',
                           check_answer_list_for_html=reversed(check_answer_list_for_html),
                           call_num=call_sum_info_for_html['call_num'],
                           sum_time_speak_wait=sec_to_hours(call_sum_info_for_html['sum_time_speak_wait']),
                           sum_time_speak=sec_to_hours(call_sum_info_for_html['sum_time_speak']),
                           sum_time_wait=sec_to_hours(call_sum_info_for_html['sum_time_wait']),
                           average_time_speak_wait=sec_to_hours(call_sum_info_for_html['average_time_speak_wait']),
                           average_time_speak=sec_to_hours(call_sum_info_for_html['average_time_speak']),
                           average_time_wait=sec_to_hours(call_sum_info_for_html['average_time_wait']),
                           startdate=startdate,
                           stoptdate=stoptdate,
                           src_=src,
                           dst_=dst,
                           status=status)


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
    return render_template('index.html',
                           check_answer_list_for_html=reversed(check_answer_list_for_html),
                           call_num=call_sum_info_for_html['call_num'],
                           sum_time_speak_wait=sec_to_hours(call_sum_info_for_html['sum_time_speak_wait']),
                           sum_time_speak=sec_to_hours(call_sum_info_for_html['sum_time_speak']),
                           sum_time_wait=sec_to_hours(call_sum_info_for_html['sum_time_wait']),
                           average_time_speak_wait=sec_to_hours(call_sum_info_for_html['average_time_speak_wait']),
                           average_time_speak=sec_to_hours(call_sum_info_for_html['average_time_speak']),
                           average_time_wait=sec_to_hours(call_sum_info_for_html['average_time_wait']),
                           startdate=startdate,
                           stoptdate=stoptdate,
                           src=src,
                           dst=dst,
                           status=status)


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


# Читаю базу данных cdr
def read_cdr(interval='hour'):
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
        except BaseException as e:
            error(str(e))
            return None
    now = now_t.strftime("%Y-%m-%d %H:%M:%S")
    delta = time_delta.strftime("%Y-%m-%d %H:%M:%S")
    query = 'SELECT * FROM cdr WHERE calldate BETWEEN "' + delta + '" AND "' + now + '"'
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


# Парсим строки с базы данных
def parser(rows, source='', dest='', disp=''):
    # (datetime.datetime(2020, 8, 26, 7, 36, 45), '"" <909>', '909', '0484163648', 'from-internal',
    # 'SIP/909-00000010', 'SIP/484164134-00000011', 'Dial', 'SIP/484164134/0484163648,300,
    # Tb(func-apply-sipheaders^s^1,(2))U(sub-send-obrout', 6, 5, 'ANSWERED', 3, '', '1598427405.16', '', '',
    # 'out-0484163648-909-20200826-073645-1598427405.16.wav', '909', '909', '909', '', '', '1598427405.16', '',
    # 16)
    # calldate | clid| src | dst | dcontext | channel| dstchannel| lastapp | lastdata  | duration | billsec |
    # disposition | amaflags | accountcode | uniqueid| userfield | did | recordingfile    | cnum | cnam|
    # outbound_cnum | outbound_cnam | dst_cnam | linkedid| peeraccount | sequence |
    if rows is None:
        return None

    call_list = list()

    # Группировка событий в 1 звонок по столбцу uniqueid
    uniqueid_list = list()
    for row in rows:
        # Если звонили с очереди
        if not row[5].find('from-queue') == -1 or row[4] == 'ext-queues':
            uniqueid_list.append(row[23][:-6])
        else:
            uniqueid_list.append(row[14])

    uniqueid_index_prep = list()
    uniqueid_index = list()
    for uniqueid in uniqueid_list:

        if uniqueid == 0:
            continue

        linkedid_flag = True
        while linkedid_flag:
            try:
                ld_index = uniqueid_list.index(uniqueid)
                uniqueid_index.append(ld_index)
                uniqueid_list[ld_index] = 0
            except BaseException as e:
                linkedid_tmp = (uniqueid, uniqueid_index.copy())
                uniqueid_index_prep.append(linkedid_tmp)
                uniqueid_index.clear()
                linkedid_flag = False

    call_time_sum = 0
    duration = 0
    dst = 0
    channel = ''

    # Анализ списка звонков, выясняем статус звонка, направление, время ожидания и разговора и т. д.
    for call in uniqueid_index_prep:
        disposition = 'FAILED'
        duration_wait = 0
        date_start = '0000-00-00 00:00:00'
        cnum = ''
        recordingfile = ''
        duration = 0

        for ii in call[1]:
            row = rows[ii]

            date_start = rows[ii][0].strftime("%Y-%m-%d %H:%M:%S")
            dst = row[3]

            channel = row[4]
            cnum = rows[ii][18]
            recordingfile = rows[ii][17]

            # Если звонят на очередь
            if not row[5].find('from-queue') == -1 or row[4] == 'ext-queues':
                if row[11] == 'ANSWERED':  # Если ответили
                    disposition = 'ANSWERED'
                    duration = row[10]
                    duration_wait = duration_wait + (int(row[9]) - int(row[10]))
                    if len(row[3]) == 3 and row[3][0] == '7':  # Пропускаю событие очереди пока не найду номер
                        continue
                    elif len(row[3]) == 3 and row[3][0] == IN_NUM:  # Нашёл номер прерываю цикл
                        break
                # Если занято, ошибка или не ответ - меняем статус звонка и начинаю цикл заново
                elif row[11] == 'BUSY' or row[11] == 'FAILED' or row[11] == 'NO ANSWER':
                    if len(row[3]) == 3 and row[3][0] == '7':  # Если номер очереди - прибаляю к времени ожидания
                        duration_wait = duration_wait + int(row[9])
                    disposition = row[11]
                    continue
            else:  # Обработка звонков не в очереди
                if row[11] == 'ANSWERED':
                    disposition = 'ANSWERED'
                    duration = row[10]
                    duration_wait = int(row[9]) - int(row[10])
                elif row[11] == 'BUSY' or row[11] == 'FAILED' or row[11] == 'NO ANSWER':
                    if disposition != 'ANSWERED':
                        disposition = row[11]
                    duration_wait = int(row[9])

            # if channel == 'ext-local':
            # elif channel == 'ext-group':
            if channel == 'from-internal-xfer':
                cnum = rows[ii][2]
            # elif channel == 'from-internal':
            elif channel == 'macro-dial':
                cnum = rows[ii][2]
            elif channel == 'ivr-1':
                cnum = rows[ii][2]
                dst = 'ivr'
                duration_wait = duration
                disposition = 'NO ANSWER'
            # elif channel == 'ext-queues':

        if channel in ('ext-local', 'ext-group', 'from-internal', 'ext-queues'):
            call_list.append((date_start, cnum, dst, disposition, duration, recordingfile, channel, duration_wait))
            call_time_sum = call_time_sum + duration  # Общее время звонка

    # Фильтрую записи
    if source != '':
        call_list_filtred = list()
        for call in call_list:
            if source == call[1] or ('38' + str(source)) == call[1] or ('+38' + str(source)) == call[1]:
                call_list_filtred.append(call)
        return call_list_filtred
    elif dest != '':
        call_list_filtred = list()
        for call in call_list:
            if dest == call[2] or ('38' + str(dest)) == call[1] + ('+38' + str(dest)) == call[1]:
                call_list_filtred.append(call)
        return call_list_filtred
    elif disp != '':
        call_list_filtred = list()
        for call in call_list:
            if disp == call[3]:
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
                call_check = isinstance(call[4], int)
                if call_check:
                    sum_time_speak = sum_time_speak + call[4]  # Общее время разговора
                else:
                    sum_time_speak = sum_time_speak + sum(x * int(t) for x, t in zip([60, 1], call[4].split(":")))
            except BaseException as e:
                info(str(e))
                sum_time_speak = sum_time_speak + 0

            sum_time_wait = sum_time_wait + call[7]  # Общее время ожидания
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


def print_call(call_list_, call_info_list):
    for call in call_list_:
        if len(call) == 7:
            print(str(call[0]) + ' ' + str(call[1]) + ' ' + str(call[2]) + ' ' + str(call[3]) + ' ' + str(call[4]) + ' '
                  + str(call[5]) + ' ' + str(call[6]))
        if len(call) == 10:
            print(str(call[0]) + ' ' + str(call[1]) + ' ' + str(call[2]) + ' ' + str(call[3]) + ' ' + str(call[4]) + ' '
                  + str(call[5]) + ' ' + str(call[6]) + ' ' + str(call[7]) + ' ' + str(call[8]) + ' ' + str(call[9]))
    print(
        'Количество звонков - ' + str(call_info_list[0]) + ' Общее время - ' + str(timedelta(seconds=call_info_list[1]))
        + ' Среднее время - ' + str(timedelta(seconds=call_info_list[2])))


# Проверка перезвона
def check_answer(calls, interval=900):
    if calls is None:
        return None
    if len(calls) == 0:
        return None

    call_check_answer = list()
    start_time = datetime.strptime(calls[0][0], "%Y-%m-%d %H:%M:%S")
    end_time = datetime.strptime(calls[len(calls) - 1][0], "%Y-%m-%d %H:%M:%S") + timedelta(seconds=int(interval))
    time_str = start_time.strftime("%Y-%m-%d %H:%M:%S") + '*' + end_time.strftime("%Y-%m-%d %H:%M:%S")
    call_list_ = parser(read_cdr(time_str))

    if call_list_ is None:
        return None

    for call in calls:
        if call[6] == 'from-internal':  # Отбрасываем внутренние номера
            continue
        if call[3] == 'ANSWERED':
            continue
        if call[3] == 'NO ANSWER':
            # Выбираем диапазон звонков в заданом интервале
            chk_call_list = list()
            answer_status = 'NO ANSWER'
            # Выясняю время звонка и задаю диапазон для поиска перезвона
            # Время звонка
            call_in_call_list_time = datetime.strptime(call[0], "%Y-%m-%d %H:%M:%S")
            # Находим индекс звонка по времени
            call_index_start = get_index_date(calls, call[0])
            # Получаю приблизительную дату конца поиска
            end_time_str = datetime.strptime(call[0], "%Y-%m-%d %H:%M:%S") + timedelta(seconds=int(interval))
            # Нахожу последний индекс диапазона звонков
            call_index_stop = get_index_date_average(call_list=call_list_,
                                                     date_end=end_time_str.strftime("%Y-%m-%d %H:%M:%S"),
                                                     index=call_index_start)
            # Делаю срез общего списка
            call_list_slice = call_list_[call_index_start:call_index_stop]

            for call_in_call_list in call_list_slice:
                # Получаю дату первого звонка в срезе
                call_in_call_list_start_time = datetime.strptime(call_in_call_list[0], "%Y-%m-%d %H:%M:%S")
                # Получаю дату последнего звонка
                call_in_call_list_time_delta = call_in_call_list_start_time + timedelta(seconds=int(interval))
                # Проверяю время звонка и сравниваю номер звонка с номеров срезе,
                if (call_in_call_list_start_time >= call_in_call_list_time) \
                        and (call_in_call_list_time_delta >= call_in_call_list_time) \
                        and shot_number(call[1]) == shot_number(call_in_call_list[2]):
                    chk_call_list.append(call_in_call_list)

            if len(chk_call_list) == 0:  # Проверяю длину списка, если пустой - не ответили
                flag_ccb = False
                # Проверяю перезванивал ли клиент
                for call_in_call_list in call_list_slice:
                    # Получаю дату первого звонка в срезе
                    call_in_call_list_start_time = datetime.strptime(call_in_call_list[0], "%Y-%m-%d %H:%M:%S")
                    # Получаю дату последнего звонка
                    call_in_call_list_time_delta = call_in_call_list_start_time + timedelta(seconds=int(interval))
                    # Проверяю время звонка и сравниваю номер звонка с номеров срезе,
                    if (call_in_call_list_start_time > call_in_call_list_time) \
                            and (call_in_call_list_time_delta >= call_in_call_list_time) \
                            and shot_number(call[1]) == shot_number(call_in_call_list[1]):
                        conv_call = list(call)
                        conv_call.append('Client call back')
                        conv_call.append(call_in_call_list[0])
                        conv_call.append(call_in_call_list[1])
                        call_check_answer.append(conv_call)
                        flag_ccb = True
                        break

                if not flag_ccb:
                    conv_call = list(call)
                    conv_call.append('Did not call back')
                    conv_call.append('0000-00-00 00:00:00')
                    conv_call.append('None')
                    call_check_answer.append(conv_call)
                continue

            for chk_call in chk_call_list:
                if chk_call[3] == 'ANSWERED':
                    answer_status = 'Call back'
                elif chk_call[3] == 'BUSY':
                    answer_status = 'Call back but busy'
                elif chk_call[3] == 'FAILED':
                    answer_status = 'Call back but failed'
                else:
                    answer_status = 'Call back no answer'

            conv_call = list(call)
            conv_call.append(answer_status)
            conv_call.append(chk_call[0])
            conv_call.append(chk_call[1])
            call_check_answer.append(conv_call)

    # Объединение списков в 1 общий
    call_check_answer_all = list()
    for call in calls:
        flag = False
        for call_ in call_check_answer:
            if call_[0] == call[0] \
                    and shot_number(call_[1]) == shot_number(call[1]) \
                    and shot_number(call_[2]) == shot_number(call[2]):
                call_check_answer_all.append(call_)
                flag = True
                break
        if not flag:
            call_check_answer_all.append(call)

    return call_check_answer_all


# Возврат индекса списка по дате
def get_index_date(call_list, key, column=0):
    index = 0
    for call in call_list:
        if key == call[column]:
            break
        else:
            index += 1

    return index


# Возврат индекса списка по дате приблизительно
def get_index_date_average(call_list, date_end, index=0, column=0, template="%Y-%m-%d %H:%M:%S"):
    index_start = index
    for call in call_list[index_start:]:
        if date_end == call[column]:
            break
        # Сравниваем даты, если дата равна или больше прерываем цикл
        elif datetime.strptime(date_end, template) <= datetime.strptime(call[column], template):
            break
        else:
            index += 1

    return index


def calls_mod(calls, call_back=False, call_back_n=False, call_back_b=False, call_back_f=False, no_call_back=False,
              cl_call_back=False):
    # 0 - ANSWERED          0 - Call back
    # 1 - NO ANSWER       1 - Call back no answer
    # 2 - BUSY              2 - Call back but busy
    # 3 - FAILED            3 - Call back but failed
    #                       4 - Did not call back
    #                       5 - Client call back
    ans_disp = 0
    if calls is None:
        mod_calls = ('', '', '', '', '', '', '', '')
        return mod_calls
    mod_calls = list()
    i = 1
    for call in calls:

        # Меняем статус звонка в цифру
        if call[3] == 'ANSWERED':
            disposition = 0
        elif call[3] == 'NO ANSWER':
            disposition = 1
        elif call[3] == 'BUSY':
            disposition = 2
        elif call[3] == 'FAILED':
            disposition = 3
        else:
            disposition = 1

        # Меняем строку ответа в цифру
        if len(call) == 11:
            if call[8] == 'Call back':
                ans_disp = 0
            elif call[8] == 'Call back no answer':
                ans_disp = 1
            elif call[8] == 'Call back but busy':
                ans_disp = 2
            elif call[8] == 'Call back but failed':
                ans_disp = 3
            elif call[8] == 'Did not call back':
                ans_disp = 4
            elif call[8] == 'Client call back':
                ans_disp = 5
            else:
                ans_disp = 3

        # Формирую список для отображения в вебе
        if len(call) == 8:
            mod_call = (
                time_shift(call[0]), shot_number(call[1]), shot_number(call[2]), disposition, sec_to_hours(call[4]),
                call[5], call[6], i, sec_to_hours(call[7]))
            if not no_call_back and not call_back_b and not call_back_f and not call_back and not call_back_n \
                    and not cl_call_back:
                mod_calls.append(mod_call)
        if len(call) == 11:
            mod_call = (
                time_shift(call[0]), shot_number(call[1]), shot_number(call[2]), disposition, sec_to_hours(call[4]),
                call[5], call[6], i, sec_to_hours(call[7]), ans_disp, mod_answer_date(call[9]), call[10])

            if call[8] == 'Did not call back' \
                    and not call_back_b \
                    and not call_back_f \
                    and not call_back \
                    and not call_back_n \
                    and not cl_call_back:
                mod_calls.append(mod_call)
            elif call[8] == 'Call back' \
                    and not call_back_b \
                    and not call_back_f \
                    and not call_back_n \
                    and not no_call_back \
                    and not cl_call_back:
                mod_calls.append(mod_call)
            elif call[8] == 'Call back no answer' \
                    and not call_back_b \
                    and not call_back_f \
                    and not call_back \
                    and not no_call_back \
                    and not cl_call_back:
                mod_calls.append(mod_call)
            elif call[8] == 'Call back but busy' \
                    and not call_back_n \
                    and not call_back_f \
                    and not call_back \
                    and not no_call_back \
                    and not cl_call_back:
                mod_calls.append(mod_call)
            elif call[8] == 'Call back but failed' \
                    and not call_back_n \
                    and not call_back_b \
                    and not call_back \
                    and not no_call_back \
                    and not cl_call_back:
                mod_calls.append(mod_call)
            elif call[8] == 'Client call back' \
                    and not call_back_n \
                    and not call_back_b \
                    and not call_back \
                    and not no_call_back \
                    and not call_back_f:
                mod_calls.append(mod_call)
            else:
                continue
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
