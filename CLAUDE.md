# Локальные правила проекта

## Развёртывание

Этот проект расположен на Ubuntu Server и подключен как сетевая папка (Z:\).

### Службы

| Компонент | Служба |
|-----------|--------|
| datacollector | `datacollector.service` |
| app | `marketplacer.service` |

**После каждого изменения проекта** выдавай пользователю команды для перезапуска служб:
```bash
sudo systemctl restart datacollector.service
sudo systemctl restart marketplacer.service
```

### База данных

- datacollector и app запущены на локальном сервере Ubuntu
- Прямой доступ к базе данных сервера
- Данные для подключения — в конфигах проекта
- Миграции и изменения БД делать напрямую, используя окружение в текущей папке

### Python окружение на Windows

Для запуска скриптов на Windows использовать виртуальное окружение:
```
C:\Users\Mike01\VSCodeProjects\MarketPlacer\venv\Scripts\python.exe
```

Пример запуска скрипта:
```powershell
powershell -Command "& 'C:\Users\Mike01\VSCodeProjects\MarketPlacer\venv\Scripts\python.exe' script.py"
```

### Git

- Коммитить после каждого изменения в текущую активную ветку
- Не пытаться посылать команды через SSH

## Общение

- Если сообщение начинается со слов "Давай подумаем" — ничего не исправлять и не изменять, только ответить на вопросы
