from datetime import timedelta


class Call:
    def __init__(self, calldate='1970-01-01 00:00:00', billsec=0, recordingfile='', context='', callwait=0,
                 disposition='NO ANSWER', duration=0, uniqueid='', linkedid='', src='', dst='', route='', answered=False
                 , npp=0, ans_disp='', ans_disp_calldate='', ans_src='', ans_dst='', comment='', hidden=False):

        self.calldate = calldate  # Дата
        self.billsec = billsec  # Время разговора
        self.recordingfile = recordingfile  # Файл с записью
        self.context = context  # Контекст
        self.callwait = callwait  # Время ожидания
        self.disposition = disposition  # Состояние звонка Ответили, Не ответили и т.д.
        self.duration = duration  # Продолжительность звонка
        self.uniqueid = uniqueid  # Уникальный ID звонка
        self.linkedid = linkedid  # Подключенный ID
        self.src = src  # Источник
        self.dst = dst  # Назначение
        self.route = route  # Направление
        self.answered = answered  # Отвечен
        self.npp = npp  # Номер по порядку
        self.ans_disp = ans_disp  # Статус неответа или неперезвона
        self.ans_disp_calldate = ans_disp_calldate  # Дата неответа
        self.ans_src = ans_src  # Источник неответа
        self.ans_dst = ans_dst  # Назначение неответа
        self.comment = comment  # Комментарий
        self.hidden = hidden  # Скрытый

    @staticmethod
    def sec_to_hours(sec):
        sec = int(sec)
        if sec < 3600:
            mod_sec = str(timedelta(seconds=sec))[2:]
        else:
            mod_sec = str(timedelta(seconds=sec))
        return mod_sec

    def durationhour(self):
        return self.sec_to_hours(self.duration)

    def billhour(self):
        return self.sec_to_hours(self.billsec)

    def callwaithour(self):
        return self.sec_to_hours(self.callwait)

    # Обрезаем 38 +38 00
    @staticmethod
    def shot_number(number):
        if len(number) == 12:
            cut_number = number[2:]
        elif len(number) == 13:
            cut_number = number[3:]
        elif len(number) == 14:
            cut_number = number[4:]
        elif len(number) == 0:
            cut_number = 'UNKNOWN'
        else:
            cut_number = number
        return cut_number

