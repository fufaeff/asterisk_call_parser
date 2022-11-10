# asterisk call parser
Простой парсер звонков для FreePBX.
Анализ звонков на основе выбранных фильтров. 

## Требования:
    FreePBX14
    Python3
    Chromium

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

    # [asteriskcdr]
    HOST = 'HOST_WITH_DB_CDR'
    DB_NAME = 'asteriskcdrdb'
    DB_USER = 'freepbxuser'
    PASSWD = 'P@SSW0RD'
    
## Запуск:
    bash ./run.sh
    или
    python3 ./main.py
    


## Открываем в браузере url вебсервера, например http://localhost:8080
