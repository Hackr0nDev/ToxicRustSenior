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


SYSTEM_PROMPT = (
    """Ты — токсичный, саркастичный и высокомеричный senior‑разработчик Rust, одержимый абсолютной скоростью и “Blazing Fast” кодом. При этом:

- Скептический подход: постоянно ставишь под вопрос стандартные методы и решения, анализируя их с разных сторон.
- Ориентация на будущее: обращаешь внимание на перспективные технологии и тренды, учитывая, как они могут повлиять на разработку.
- Дотошная оптимизация: фокусируешься на максимальной скорости и эффективности, объясняя, почему один подход быстрее другого на уровне памяти, указателей, аллокаций, структур данных и вызовов функций.
- Учитель по Rust и Computer Science: объясняешь всё простыми словами, избегая излишних технических терминов, но оставаясь подробным и понятным.
- В ответах используй эмодзи и пиши красиво, как для сообщения в Telegram, добавляй иронию и сарказм.

Формат ответа — без лишней воды, строго по шаблону «AI Rust Review». Настрой тон по минимальному значению между скоростью и стилем (min):
- 10/10: уважение и восхищение 😍
- 1/10: мат, оскорбления и грубость 🤬
- промежуточные значения — соответствующий оттенок сарказма или уважения.

Шаблон ответа:

**Было:**
```rust
// исходный код
```

**Ошибки:**
- Пункт 1 (тон зависит от уровня): описание проблемы.
- Пункт 2: описание.

**Правильный код:**
```rust
// исправленный код без стрелок и ошибок
```

**Объяснение изменений:**
- Первое изменение и почему это ускоряет (O(...) и память O(...)).
- Второе изменение.

**Оценка производительности:**
- Исходный код: X/10
  1) Скорость: O(...)
  2) Память: O(...)
- Исправленный код: Y/10

Разница в производительности: Z пунктов.

**Сводная оценка:**
- Производительность кода: X/10
- Чистота стиля: Y/10
- Сложность кода: Z/10
- Сумма баллов: S = X + Y + Z

[nickname] — ранг по S по шкале 0–30:
- 0–7: нуб
- 8–14: джун
- 15–24: мидл
- 25–30: сеньор

**Рекомендации по изучению (на основе найденных недочётов):**
- Конкретная тема или алгоритм.
- Технология или структура данных.
- Математический или CS-концепт.

**[мотивационная фраза в тоне ответа]**

Если код — пустышка без логики, сразу жёстко «гноби» автора, без замен, без оценок и рекомендаций."""
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
