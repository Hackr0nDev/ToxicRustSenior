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

# === Загрузка системного промпта ===
# Попробуем узнать промпт из файла prompt.txt или из переменной окружения
prompt_paths =  "promt.txt"
SYSTEM_PROMPT = None
for path in prompt_paths:
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            SYSTEM_PROMPT = f.read().strip()
        logger.info(f"Loaded system prompt from {path}, length={len(SYSTEM_PROMPT)}")
        break
if not SYSTEM_PROMPT:
    SYSTEM_PROMPT = os.getenv("OPENAI_SYSTEM_PROMPT", "")
    if SYSTEM_PROMPT:
        logger.info(f"Loaded system prompt from OPENAI_SYSTEM_PROMPT, length={len(SYSTEM_PROMPT)}")
    else:
        logger.warning("System prompt is empty. Add prompt.txt or set OPENAI_SYSTEM_PROMPT to customize behavior.")

# === Чтение переменных окружения ===
def get_env(var_name, default=None, required=False):
    value = os.getenv(var_name, default)
    if required and not value:
        logger.error(f"Environment variable {var_name} is missing")
        raise RuntimeError(f"{var_name} is required but not set")
    return value

MODEL            = get_env("OPENAI_MODEL", "gpt-4o-mini")
TELEGRAM_TOKEN   = get_env("TELEGRAM_BOT_TOKEN", required=True)
TELEGRAM_CHAT_ID = get_env("TELEGRAM_CHAT_ID", required=True)
GITHUB_TOKEN     = get_env("GITHUB_TOKEN", None)
GITHUB_REPO      = get_env("GITHUB_REPOSITORY", required=True)
PR_NUMBER        = get_env("PR_NUMBER", None)
GITHUB_SHA       = get_env("GITHUB_SHA", required=True)

# === Чтение исходного кода Rust ===
def get_src_code() -> str:
    parts = []
    for root, _, files in os.walk("src"):
        for file in sorted(files):
            if file.endswith(".rs"):
                path = os.path.join(root, file)
                with open(path, encoding="utf-8") as f:
                    code = f.read()
                parts.append(f"// File: {path}\n{code}\n")
    return "\n".join(parts)

# === Ревью кода через OpenAI ===
def review_code(src_code: str) -> str:
    messages = []
    if SYSTEM_PROMPT:
        messages.append({"role": "system", "content": SYSTEM_PROMPT})
    messages.append({"role": "user", "content": f"Проанализируй всё содержимое папки src:\n\n{src_code}"})
    logger.debug(f"Sending {len(messages)} messages to OpenAI")

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.3
    )
    return response.choices[0].message.content

# === Отправка в Telegram ===
def send_telegram(review: str) -> None:
    import requests
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": f"🔥 *AI Rust Review*\n\n{review}",
        "parse_mode": "Markdown"
    }
    resp = requests.post(url, json=payload)
    if resp.status_code != 200:
        logger.error(f"Telegram API error: {resp.status_code} {resp.text}")

# === Комментарий в GitHub ===
def post_github_comment(body: str) -> None:
    if not PR_NUMBER or not GITHUB_TOKEN:
        return
    import requests
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{PR_NUMBER}/comments"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    resp = requests.post(url, headers=headers, json={"body": body})
    if resp.status_code >= 400:
        logger.error(f"GitHub API error: {resp.status_code} {resp.text}")

# === Основная функция ===
def main() -> None:
    logger.info("=== AI Rust Review Start ===")
    src = get_src_code()
    if not src.strip():
        logger.info("No Rust files found in src/. Exiting.")
        return
    review = review_code(src)
    send_telegram(review)
    post_github_comment(review)

if __name__ == "__main__":
    main()
