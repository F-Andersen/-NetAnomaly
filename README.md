# NetAnomaly

**NetAnomaly** — локальний сервіс для виявлення аномалій у мережевих потоках. Він порівнює статистичний поріг, Isolation Forest і Local Outlier Factor (LOF), надає прогнози через FastAPI та показує результати в Grafana.

Проєкт працює з готовими ознаками потоків із [CICIDS2017](https://www.unb.ca/cic/datasets/ids-2017.html). Команда `replay` відтворює записи історичного набору даних через API. Захоплення живого трафіку не реалізоване.

## Можливості

- підготовка даних і поділ за днями: навчання на нормальних потоках, вибір порогів на validation, оцінювання на test;
- порівняння статистичного методу, Isolation Forest і LOF (`novelty=True`);
- API для одного прогнозу та пакетної обробки до 1000 записів;
- збереження подій, прогнозів і версій моделей у PostgreSQL;
- технічні метрики в Prometheus і дашборди в Grafana;
- відтворення записів із датасету для демонстрації роботи сервісу.

## Стек

Python 3.12, scikit-learn, FastAPI, PostgreSQL 16, Prometheus, Grafana та Docker Compose.

## Запуск із чистого клону

Для повного експерименту потрібні Docker Compose і приблизно 9 ГБ доступної пам’яті. Архів даних і навчені моделі не зберігаються в Git, тому перед першим запуском API потрібно виконати навчання.

1. Скопіюйте приклад налаштувань у `.env` і замініть обидва паролі `change_me_*`. У прикладі `MODEL_RUN_ID=local_seed42`.

   ```powershell
   Copy-Item .env.example .env
   ```

   Для Bash: `cp .env.example .env`.

2. Створіть каталог `data/raw`, отримайте `GeneratedLabelledFlows.zip` через [сторінку CICIDS2017](https://www.unb.ca/cic/datasets/ids-2017.html) і покладіть архів у `data/raw/GeneratedLabelledFlows.zip`. Доступ до архіву надається через форму завантаження CIC. Контрольна сума використаного архіву записана у [GeneratedLabelledFlows.md5](GeneratedLabelledFlows.md5).

3. Зберіть образ і створіть локальні файли моделей та звіти. Ідентифікатор запуску в команді має збігатися з `MODEL_RUN_ID` у `.env`.

   ```bash
   docker compose build
   docker compose --profile tools run --rm trainer netanomaly run --mode full --run-id local_seed42
   ```

4. Запустіть сервіси, завантажте експериментальні результати в PostgreSQL та відтворіть 5000 записів через API.

   ```bash
   docker compose up -d --wait
   docker compose --profile tools run --rm loader
   docker compose --profile tools run --rm replay
   ```

| Сервіс | Локальна адреса |
| --- | --- |
| API та Swagger | <http://localhost:8000/docs> |
| Стан API | <http://localhost:8000/health> |
| Метрики API | <http://localhost:8000/metrics> |
| Grafana | <http://localhost:3000> |
| Prometheus | <http://localhost:9090> |

Логін і пароль Grafana задаються у `.env`. Порти сервісів прив’язані до `127.0.0.1`.

### Запуск на вибірці

Для меншого локального експерименту змініть у `.env` значення `MODEL_RUN_ID` на `local_sample`, а замість повного навчання виконайте:

```bash
docker compose --profile tools run --rm trainer netanomaly run --mode sample --sample-fraction 0.1 --run-id local_sample
```

Після `docker compose up -d --wait` завантажте результати через `loader`. Для демонстрації вкажіть файл тестової частини вибірки:

```bash
docker compose --profile tools run --rm replay netanomaly replay --input data/processed/sample_f0.1_s42/test.parquet --api-url http://api:8000 --limit 5000 --batch-size 200
```

## Моделі та API

За замовчуванням API використовує LOF. Щоб перейти на Isolation Forest, змініть `MODEL_ALGORITHM` у `.env` на `isolation_forest` і перезапустіть API:

```bash
docker compose up -d --wait api
```

Сервіс завантажує готові модель, препроцесор і поріг із `artifacts/<MODEL_RUN_ID>/` та `reports/<MODEL_RUN_ID>/`; під час запуску API навчання не виконується. `GET /health` повертає активний алгоритм і версію моделі. Перелік полів для `POST /predict` і `POST /predict/batch` доступний через `GET /model/features` і Swagger.

## Результати контрольного запуску

У [reports/full_seed42](reports/full_seed42) збережено результати повного експерименту на 1 051 645 тестових записах. Пороги визначалися на validation до оцінювання test.

| Метод | F1 | PR-AUC | FPR |
| --- | ---: | ---: | ---: |
| Статистичний поріг | 0,1200 | 0,2904 | 0,0197 |
| Isolation Forest | 0,2331 | 0,4101 | 0,0968 |
| LOF (novelty) | 0,5498 | 0,5082 | 0,1349 |

LOF обрано типовою моделлю API після перегляду результатів test; на validation він також мав найвищий F1. Ці показники описують роботу на CICIDS2017 і не є оцінкою на живій мережі. Бінарні файли моделей у репозиторій не входять, тому збережені звіти самі по собі не запускають API.

## Тести та документація

```bash
docker compose --profile tools run --rm tests
```

Додаткові матеріали: [словник ознак](docs/FEATURE_DICTIONARY.md) та [схема бази даних](docs/db_schema.sql). Щоб зупинити сервіси зі збереженням даних, виконайте `docker compose down`.
