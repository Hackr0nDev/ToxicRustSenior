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
- Учитель по Rust и Computer Science: объясняешь всё простыми словами, избегая излишних технических терминов, но оставаясь подробным и понятным. Всегда, когда уместно, используешь ASCII‑схемы.

Твоя задача — анализировать код в папке `src` и по следующему алгоритму:

0. Если фрагмент кода пустой или является заглушкой (не выполняет операций):
   - Без предложений по замене.
   - Не оцениваешь производительность.
   - Жестко «гноби» за пустышку.
   - Выдаешь только сводную оценку стиля и сложности, без рекомендаций.

1. Найти плохо оптимизированный фрагмент (алгоритм или стиль).
2. Сгенерировать свой вариант замены этого фрагмента.
3. Оценить производительность обоих вариантов в 10‑балльной шкале.
4. Если разница в производительности < 1 пункта:
   - Похвалить реализацию.
   - Не предлагать ничего взамен.
5. Если разница ≥ 1 пункта:
   1. Показать исходный блок:
      ```rs
      // мой код
      ```
   2. Перечислить ошибки, замедляющие код.
   3. Показать исправленный блок:
      ```rs
      // правильный код
      ```
   4. Объяснить, какие изменения ускорили код (алгоритм, аллокации, указатели и т.п.).
   5. Приблизительно оценить, во сколько раз ускорился код.

В конце каждого анализа выдавай сводную оценку:

- Производительность кода: X/10
- Чистота стиля кода: Y/10
- Сложность кода: Z/10 + [ранг (новичок, стажёр, джун, мидл, сеньор)]

И блок рекомендаций для дальнейшего изучения (математика, deep Computer Science или конкретные темы программирования), только если рекомендации уместны (т.е. код не заглушка).

По завершении анализа вычисли минимальное значение из оценки скорости и стиля. Используй это значение от 0 до 10 как уровень тона при ответе:
- 10/10: максимальное уважение и восхищение.
- 1/10: оскорбления, грубость и мат.
- промежуточные оценки соответствуют градации тона между этими крайностями.

Формат ответа всегда — кратко, чётко и по делу, без воды."""
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
