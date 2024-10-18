# asterisk call parser
Простой парсер звонков для FreePBX.
Анализ звонков на основе выбранных фильтров. 

## Требования:
    FreePBX/Issabel
    Python3
    

## Установка:
    python3 -m pip install -r ./requirements.txt
    

## Настройка:
    Добавляем файл config/settings.py
    
    # [webserver]
    FLASK_ADDRESS = '0.0.0.0'
    FLASK_PORT = 8080
    # [system]
    CHECK_ANSWER_INTERVAL = 3600
    PATH_TO_ASTERISK_MONITOR = '/var/spool/asterisk/monitor/'
    ASTERISK_DISTR='ISSABEL'

    # [asteriskcdr]
    HOST = 'HOST_WITH_DB_CDR'
    DB_NAME = 'asteriskcdrdb'
    DB_USER = 'freepbxuser'
    PASSWD = 'P@SSW0RD'
    
## Запуск:
    bash ./run.sh
    или
    python3 ./main.py
    
## Получить данные с таблицы cdr:

* curl -X POST http://localhost:8080/read_cdr/ -H 'Content-Type: application/json' -d '{"interval":"hour"}'

         "interval" возможные значения:

         "hour" - 1 час
         "day"  - 1 день
         "week" - 1 неделя
         "month" - 1 месяц
         "year"  - 1 год
         задать интервал вручную - шаблон "%Y-%m-%d %H:%M:%S*%Y-%m-%d %H:%M:%S" 
            Например: 
            curl -X POST http://localhost:8080/read_cdr/ -H 'Content-Type: application/json' -d '{"interval":"2022-08-16 11:00:00*2022-08-16 09:00:00"}'

## Открываем в браузере url вебсервера, например http://localhost:8080
