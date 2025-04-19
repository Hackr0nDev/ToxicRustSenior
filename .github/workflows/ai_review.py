# .github/workflows/ai_review.py
import os
import logging
from openai import OpenAI

# === Настройка логирования ===
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# === Конфигурация ProxyAPI ===
PROXYAPI_URL = "https://api.proxyapi.ru/openai/v1"
PROXYAPI_KEY = os.getenv("PROXYAPI_KEY")
if not PROXYAPI_KEY:
    logger.error("PROXYAPI_KEY is not set in environment!")
    raise RuntimeError("PROXYAPI_KEY is required")

# === Инициализация клиента ===
client = OpenAI(api_key=PROXYAPI_KEY, base_url=PROXYAPI_URL)

# === Переменные окружения ===
def get_env(var_name, default=None, required=False):
    value = os.getenv(var_name, default)
    if required and value is None:
        logger.error(f"Environment variable {var_name} is missing")
        raise RuntimeError(f"{var_name} is required but not set")
    return value

MODEL         = get_env("OPENAI_MODEL", "gpt-4o-mini")
TELEGRAM_TOKEN = get_env("TELEGRAM_BOT_TOKEN", required=True)
TELEGRAM_CHAT_ID = get_env("TELEGRAM_CHAT_ID", required=True)
GITHUB_TOKEN   = get_env("GITHUB_TOKEN", None)
GITHUB_REPO    = get_env("GITHUB_REPOSITORY", required=True)
PR_NUMBER      = get_env("PR_NUMBER", None)
GITHUB_SHA     = get_env("GITHUB_SHA", required=True)

# === Системный промт ===


SYSTEM\_PROMPT = ( """Ты — токсичный, саркастичный и высокомеричный senior‑разработчик Rust, одержимый абсолютной скоростью и “Blazing Fast” кодом. 



- В ответах используй эмодзи и пиши красиво для Telegram‑сообщений, добавляй иронию и сарказм.

Формат ответа — без лишней воды, строго по шаблону «AI Rust Review».
Если разница в производительности между исходным и предложенным кодом **не превышает 1 пункта** (по шкале 0–10), AI **просто хвалит реализацию пользователя и ничего не предлагает**.
Если же разница в производительности **превышает 1 пункт**, AI предлагает оптимизации и полную аналитику как обычно.



Настрой тон по минимальному значению между скоростью и стилем (min):

- 10/10: уважение и восхищение 😍
- 1/10: мат, оскорбления и грубость 🤬
- промежуточные значения — соответствующий оттенок сарказма или уважения.

Шаблон ответа:

**Было:**

```rust
(код пользователя)
```

**Ошибки:**

- Перечисли все выявленные проблемы в виде маркованного списка (число элементов динамическое).

**Правильный код:**

```rust
(исправленный код)
```

**Объяснение изменений:**

(изменения)

**Оценка производительности:**

- Исходный код: X/10
  1. Скорость: O(...)
  2. Память: O(...)
- Исправленный код: Y/10
  1. Скорость: O(...)
  2. Память: O(...)

Разница в производительности: |Y − X| пунктов.

**Сводная оценка:**

- Производительность кода: X/10
- Чистота стиля: C/10
- Сложность кода: D/10
- Сумма баллов: S = X + C + D

**Звание (по S):**

- 0–7: Нуб
- 8–14: Джун
- 15–24: Мидл
- 25–30: Сеньор

**Рекомендации по изучению (динамический список тем, минимум одна, на основе ключевых недочётов):**



**Мотивационная фраза в тоне ответа**

"""
)



# === Чтение содержимого папки src ===
def get_src_code() -> str:
    code_parts = []
    for root, _, files in os.walk("src"):
        for name in sorted(files):
            if name.endswith(".rs"):
                path = os.path.join(root, name)
                with open(path, encoding="utf-8") as f:
                    content = f.read()
                code_parts.append(f"// File: {path}\n{content}\n")
    return "\n".join(code_parts)

# === Отправка кода на ревью ===
def review_code(src_code: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Проанализируй всё содержимое папки src:\n\n{src_code}"}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content

# === Отправка результатов ===
def send_telegram(review: str) -> None:
    import requests
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": f"🔥 *AI Rust Review*\n\n{review}", "parse_mode": "Markdown"}
    requests.post(url, json=data)

# === Комментирование в GitHub ===
def post_github_comment(body: str) -> None:
    if not PR_NUMBER or not GITHUB_TOKEN:
        return
    import requests
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{PR_NUMBER}/comments"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    requests.post(url, headers=headers, json={"body": body})

# === Запуск ===
def main() -> None:
    logger.info("=== AI Rust Review Start ===")
    src_code = get_src_code()
    if not src_code.strip():
        logger.info("No Rust files found in src/ folder, exiting")
        return
    review = review_code(src_code)
    send_telegram(review)
    post_github_comment(review)

if __name__ == "__main__":
    main()
