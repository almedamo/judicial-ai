# judicial-ai-starter

Минимальный прототип для проверки конвейера. XML поддерживается в простом учебном формате; судебные XML ФССП требуют адаптации под схему из датасета. Классификация по фразам и регулярные выражения — baseline, не качественная готовая модель. Сканы читаются Tesseract OCR (rus). Обученный классификатор — отдельный эксперимент и не используется API до интеграции.

```bash
cp .env.example .env
docker compose up --build -d
curl http://localhost:8000/health
curl -F "files=@samples/court_order.txt" http://localhost:8000/api/v1/batches
```

В ответе найдите `job_id`, затем скачайте результат:

```bash
curl -OJ http://localhost:8000/api/v1/jobs/JOB_ID/result.xlsx
```

Для обучения модели подготовьте `data/train.csv` с колонками `text,label`; метки: `court_order`, `writ_of_execution`, `fssp_resolution`. Скрипт требует минимум 8 строк и минимум 2 класса, для стратифицированной выборки минимум по 2 на класс. Демо-CSV недостаточен для оценки качества.

```bash
python training/train_classifier.py --input data/train.csv --output artifacts/classifier.joblib
```

Email пока не отправляется: флаг `needs_legal_review` есть в таблице, SMTP-интеграция остаётся следующей задачей.
