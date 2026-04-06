# Mythoria Forum — Railway Deploy

## Структура проекта
```
mythoria-railway/
├── server.py          # FastAPI сервер
├── requirements.txt   # Python зависимости
├── Procfile           # Команда запуска для Railway
├── railway.json       # Конфиг Railway
├── .gitignore
└── static/
    └── index.html     # Весь фронтенд
```

## Запуск локально (Termux)
```bash
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000
```

## Деплой на Railway
1. Загрузить папку на GitHub
2. Подключить репо в railway.app
3. Добавить PostgreSQL плагин
4. Готово — DATABASE_URL подхватится автоматически
