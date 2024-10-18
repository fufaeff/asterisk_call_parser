from logging import error, info
from datetime import datetime, timedelta
from pymysql import connect, Error
from pymysql.cursors import DictCursor
from contextlib import closing
from config.settings import *

from libs.classes import Call


# Парсим строки с базы данных
def parser(rows, source='', dest='', disp=''):
    # Проверка на совпадение с фильтром
    def call_filter(call_):
        include = False
        if source != '':
            if source == call_.shot_number(call_.src):
                include = True

        if dest != '':
            if dest == call_.shot_number(call_.dst):
                include = True

        if disp != '':
            if disp in (call_.disposition, call_.ans_disp):
                include = True

        return include

    # Если пустой список с базы возвращяю пусто
    if rows is None:
        return None

    call_list = []
    uniqueid_calls_dict = {}

    # Группировка событий по linkedid и uniqueid
    # Выбираю записи с совпадающими полями linkedid и uniqueid
    for uniq_call in rows.copy():
        uniqueid = uniq_call['uniqueid']
        uniqueid_split = uniqueid.split('.')
        uniqueid_prefix = uniqueid_split[0]

        # Создаю список uniqueid
        if uniqueid_calls_dict.get(uniqueid_prefix) is None:  # Если первое совпадение создаю новый ключ
            uniqueid_calls_dict.update({uniqueid_prefix: [uniq_call]})
        else:  # Обновляю ключ добавляя поле
            exist_calls = uniqueid_calls_dict[uniqueid_prefix]
            exist_calls.append(uniq_call)
            uniqueid_calls_dict.update({uniqueid_prefix: exist_calls})
        rows.remove(uniq_call)

    # Выхожу если пустой список
    if len(uniqueid_calls_dict) == 0:
        return None

    # Анализ списка звонков, выясняем статус звонка, направление, время ожидания и разговора и т. д.
    dict(sorted(uniqueid_calls_dict.items()))
    for uniqueid, uniq_calls in uniqueid_calls_dict.items():
        uniqueid_calls_list_sorted = sorted(uniq_calls, key=lambda d: d['calldate'])  # Сортирую по времени
        call_info = Call()
        call_info.uniqueid = uniqueid

        for uniq_call in uniqueid_calls_list_sorted:
            # call_info.hidden = False

            if uniq_call['dcontext'] in 'from-internal':
                if ASTERISK_DISTR == 'ISSABEL':  # Проверяем дистрибутив астериска
                    if uniq_call['lastapp'] == 'AppDial2':  # если контекст вызова с C2C
                        call_info.src = uniq_call['src']
                        call_info.dst = uniq_call['channel'].split('/')[1].split('-')[0]
                    else:
                        call_info.src = uniq_call['cnum']
                        call_info.dst = uniq_call['dst']
                    # call_info.src = uniq_call['src']
                else:
                    call_info.src = uniq_call['cnum']
                    call_info.dst = uniq_call['dst']

            elif uniq_call['dcontext'] == 'ext-local':  # Обработка недозвона с очереди
                call_info.src = uniq_call['cnum']
                call_info.dst = uniq_call['dst']
                if uniq_call['disposition'] != 'ANSWERED':
                    if uniq_call['channel'].find('@from-queue') != -1:  # Проверяю что канал очереди
                        try:
                            call_info.dst = uniqueid_calls_dict.get(uniq_call['linkedid'].split('.')[0])[0][
                                'dst']  # Выбираю номер очереди по linkedid
                            call_info.callwait = uniq_call['duration']
                        except BaseException as e:
                            error(str(e))
                            continue

            elif uniq_call['dcontext'] == 'from-internal-xfer':
                if ASTERISK_DISTR == 'ISSABEL':  # Проверяем дистрибутив астериска
                    if uniq_call['lastapp'] == 'AppDial':
                        call_info.src = uniq_call['src']
                        call_info.dst = uniq_call['channel'].split('/')[1].split('-')[0]
                    elif uniq_call['lastapp'] == '':
                        call_info.hidden = True
                    else:
                        call_info.src = uniq_call['src']
                else:
                    call_info.src = uniq_call['cnum']
                call_info.dst = uniq_call['dst']

            elif uniq_call['dcontext'] == 'from-trunk':
                if ASTERISK_DISTR == 'ISSABEL':  # Проверяем дистрибутив астериска
                    if uniq_call['lastapp'] == 'AppDial':
                        call_info.src = uniq_call['src']
                        call_info.dst = uniq_call['dstchannel'].split('/')[1].split('-')[0]
                    else:
                        call_info.src = uniq_call['src']
                else:
                    call_info.src = uniq_call['cnum']
                    call_info.dst = uniq_call['dst']

            elif uniq_call['dcontext'] == 'app-blacklist-remove':
                continue

            elif uniq_call['dcontext'] == 'macro-dial-one':  # обработка переводов
                if uniq_call['lastapp'] == 'Dial':
                    call_info.src = uniq_call['src']
                    if uniq_call['dstchannel'] != '':
                        call_info.dst = uniq_call['dstchannel'].split('@')[0].split('/')[1]
                else:
                    if len(uniqueid_calls_list_sorted) == 1:
                        call_info.hidden = True
                    continue

            elif uniq_call['dcontext'] == 'macro-dial':  # Обработка перевода
                if uniq_call['lastapp'] == 'Dial':
                    call_info.src = uniq_call['src']
                    if uniq_call['dstchannel'] != '':
                        call_info.dst = uniq_call['dstchannel'].split('@')[0].split('/')[1]
                elif uniq_call['lastapp'] == 'ExecIf':
                    call_info.dst = uniq_call['src']
                    if uniq_call['dstchannel'] != '':
                        try:
                            call_info.src = uniqueid_calls_dict.get(uniq_call['linkedid'].split('.')[0])[0][
                                'src']
                            call_info.hidden = True
                        except BaseException as e:
                            error(str(e))
                            continue
                    else:
                        continue
                else:
                    call_info.hidden = True
                    continue

            elif uniq_call['dcontext'] == 'ext-group':
                if uniq_call['dstchannel'].find('SIP') != -1 and uniq_call['disposition'] == 'ANSWERED':
                    call_info.src = uniq_call['src']
                    call_info.dst = uniq_call['dstchannel'].split('/')[1].split('-')[0]  # 'SIP/125-00008a71'
                    if call_info.dst.find('@') != -1:
                        call_info.dst = call_info.dst.split('@')[0]
                    if uniq_call['disposition'] == 'NO ANSWER':
                        call_info.callwait = call_info.callwait + uniq_call['duration']
                elif not call_info.answered:
                    call_info.src = uniq_call['src']
                    call_info.dst = uniq_call['dst']
            # elif uniq_call['dcontext'] == 'ext-queues':
            #     if uniq_call['disposition'] != 'ANSWERED':
            #         if not call_info.answered:
            #             call_info.src = uniq_call['src']
            #             call_info.dst = uniq_call['dst']

            else:
                call_info.src = uniq_call['src']
                call_info.dst = uniq_call['dst']

            call_info.calldate = uniq_call['calldate'].strftime("%Y-%m-%d %H:%M:%S")
            if uniq_call['recordingfile'] != '':  # Проверяем чтобы небыл пустым
                call_info.recordingfile = uniq_call['recordingfile']
            call_info.context = uniq_call['dcontext']

            if uniq_call['disposition'] == 'ANSWERED':
                call_info.answered = True
                call_info.disposition = 'ANSWERED'
                call_info.billsec = uniq_call['billsec']
                if call_info.callwait == 0:
                    call_info.callwait = uniq_call['duration'] - uniq_call['billsec']

            call_info.linkedid = uniq_call['linkedid'].split('.')[0]

        call_info.src = call_info.shot_number(call_info.src)
        call_info.dst = call_info.shot_number(call_info.dst)
        call_list.append(call_info)

        # Проверка linkedid вхождения в uniqueid
    for call_info in call_list:
        if call_info.uniqueid == call_info.linkedid:  # Если совпадает пропускаем
            continue
        else:
            # if call_info.disposition == 'ext-queues':
            if not call_info.answered:  # Если не отвеченный, проверяем был ли ответ на основном id
                for call_info_ in call_list:
                    if call_info_.uniqueid == call_info.linkedid:
                        # if call_info_.answered:  # Если был ответ на уникальном id, скрываем звонок.
                        call_info.hidden = True

    if dest != '' or source != '' or disp != '':  # Если включен фильтр
        call_list_filtred = []
        for uniq_call in call_list:
            if call_filter(uniq_call):
                call_list_filtred.append(uniq_call)
        return call_list_filtred
    else:
        return call_list


# Проверка перезвона
def check_answer(calls, interval=900):
    if calls is None:
        return None
    if len(calls) == 0:
        return None

    calls_with_answers = []
    for call in calls:
        if call.context == 'from-internal':  # Отбрасываем внутренние номера
            calls_with_answers.append(call)
            continue
        if call.disposition == 'ANSWERED':
            calls_with_answers.append(call)
            continue
        if call.disposition == 'NO ANSWER':
            # Выбираем диапазон звонков в заданом интервале
            chk_call_list = list()
            # Время звонка
            call_start = datetime.strptime(call.calldate, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")

            # Получаю дату конца поиска
            end_time_str = (datetime.strptime(call.calldate, "%Y-%m-%d %H:%M:%S") + timedelta(
                seconds=int(interval))).strftime("%Y-%m-%d %H:%M:%S")

            # Выбираю записи за период
            interval_slice = f'{call_start}*{end_time_str}'
            calls_list_slice = parser(read_cdr(interval=interval_slice, dict_cursor=True), source=call.src,
                                      dest=call.src)

            # Отбираю звонки где упоминается src
            try:
                for call_in_slice in calls_list_slice:
                    call_src = call.shot_number(call.src)
                    slice_disp = call_in_slice.disposition
                    slice_src = call.shot_number(call_in_slice.src)
                    slice_dst = call.shot_number(call_in_slice.dst)
                    if (slice_src == call_src and slice_disp == 'ANSWERED') or (
                            slice_dst == call_src and slice_disp == 'ANSWERED'):
                        chk_call_list.append(call_in_slice)
            except BaseException as e:
                error(str(e))

            if len(chk_call_list) == 0:  # Проверяю длину списка, если пустой - не ответили или не перезвонили
                call.ans_disp = 'Did not call back'
                call.ans_disp_calldate = call.calldate

            else:
                ans_disp = 'Did not call back'
                for chk_call in chk_call_list:
                    if chk_call.disposition == 'ANSWERED':
                        if call == chk_call:
                            continue
                        elif chk_call.context in ('ext-group', 'ext-local'):

                            if chk_call.src == call.src:
                                ans_disp = 'Client call back'
                            else:
                                ans_disp = 'Call back'
                            call.ans_disp = ans_disp
                            call.ans_disp_calldate = chk_call.calldate
                            call.ans_src = chk_call.src
                            call.ans_dst = chk_call.dst
                            break
                        else:
                            ans_disp = 'Call back'
                    elif chk_call.disposition == 'BUSY':
                        ans_disp = 'Call back but busy'
                    elif chk_call.disposition == 'FAILED':
                        ans_disp = 'Call back but failed'
                    else:
                        ans_disp = 'Call back no answer'

                    if ans_disp != 'Did not call back':
                        call.ans_disp = ans_disp
                        call.ans_disp_calldate = chk_call.calldate
                        call.ans_src = chk_call.src
                        call.ans_dst = chk_call.dst
                        break
                else:
                    call.ans_disp = ans_disp
                    call.ans_disp_calldate = call.calldate
                    call.ans_src = call.src
                    call.ans_dst = call.dst
        calls_with_answers.append(call)
    return calls_with_answers


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


def calls_mod(calls):
    # 0 - ANSWERED          0 - Call back
    # 1 - NO ANSWER         1 - Call back no answer
    # 2 - BUSY              2 - Call back but busy
    # 3 - FAILED            3 - Call back but failed
    #                       4 - Did not call back
    #                       5 - Client call back

    if calls is None:
        return []

    i = 1
    for call in calls:
        # Формирую список для отображения в вебе

        call.calldate = time_shift(call.calldate)
        call.src = call.shot_number(call.src)
        call.dst = call.shot_number(call.dst)
        call.npp = i
        i += 1
    return calls


# Корректировка отображения времени
def time_shift(date_):
    s_time = datetime.strptime(date_, "%Y-%m-%d %H:%M:%S")
    return s_time.strftime("%Y-%m-%d %H:%M:%S")


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
                call_check = isinstance(call.billsec, int)
                if call_check:
                    sum_time_speak = sum_time_speak + call.billsec  # Общее время разговора
                else:
                    sum_time_speak = sum_time_speak + sum(
                        x * int(t) for x, t in zip([60, 1], call.billsec.split(":")))
            except BaseException as e:
                info(str(e))
                sum_time_speak = sum_time_speak + 0

            sum_time_wait = sum_time_wait + call.callwait  # Общее время ожидания
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
