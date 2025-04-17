# .github/workflows/ai_review.py
import os
import requests
import subprocess
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
PROXYAPI_URL = "https://api.proxyapi.ru/openai/v1"  # фиксированный URL согласно докам
PROXYAPI_KEY = os.getenv("PROXYAPI_KEY")
if not PROXYAPI_KEY:
    logger.error("PROXYAPI_KEY is not set in environment!")
    raise RuntimeError("PROXYAPI_KEY is required")
logger.debug(f"Using PROXYAPI_URL={PROXYAPI_URL}")

# === Инициализация клиента ===
try:
    client = OpenAI(api_key=PROXYAPI_KEY, base_url=PROXYAPI_URL)
    logger.debug("OpenAI client initialized successfully")
except Exception as e:
    logger.exception("Failed to initialize OpenAI client: %s", e)
    raise

# === Прочие переменные среды ===
def get_env(var_name, default=None, required=False):
    value = os.getenv(var_name, default)
    if required and value is None:
        logger.error(f"Environment variable {var_name} is missing")
        raise RuntimeError(f"{var_name} is required but not set")
    logger.debug(f"ENV {var_name}={value}")
    return value

MODEL = get_env("OPENAI_MODEL", "gpt-4")
TELEGRAM_TOKEN = get_env("TELEGRAM_BOT_TOKEN", required=True)
TELEGRAM_CHAT_ID = get_env("TELEGRAM_CHAT_ID", required=True)
GITHUB_TOKEN = get_env("GITHUB_TOKEN", None)
GITHUB_REPO = get_env("GITHUB_REPOSITORY", required=True)
PR_NUMBER = get_env("PR_NUMBER", None)
COMMIT_SHA = get_env("GITHUB_SHA", required=True)

SYSTEM_PROMPT = (
    "Ты токсичный, высокомерный senior-разработчик, одержимый оптимизацией."
    " Формат ответа:\nКомментарий\n```rs\n<код>\n```"
)
logger.debug("SYSTEM_PROMPT set")

# === Функции ===
def get_diff() -> str:
    logger.debug("Running git diff HEAD~1 HEAD")
    proc = subprocess.run(["git", "diff", "HEAD~1", "HEAD"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        logger.error("git diff failed: %s", proc.stderr)
        raise RuntimeError("git diff command failed")
    logger.debug("git diff output length: %d chars", len(proc.stdout or ""))
    return proc.stdout


def review_code(diff: str) -> str:
    logger.debug("Preparing chat completion request")
    logger.debug(f"Request diff snippet: {diff[:200].replace(chr(10), ' ')}...")
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Вот diff кода:\n\n{diff}"}
            ],
            temperature=0.7
        )
        logger.debug("Chat completion response received")
        content = response.choices[0].message.content
        logger.debug(f"Review content length: {len(content)}")
        return content
    except Exception as e:
        logger.exception("Error during chat completion: %s", e)
        raise


def post_github_comment(body: str) -> None:
    if not PR_NUMBER:
        logger.info("No PR_NUMBER set, skipping GitHub comment")
        return
    if not GITHUB_TOKEN:
        logger.warning("GITHUB_TOKEN not set, cannot post comment")
        return
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{PR_NUMBER}/comments"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    payload = {"body": body}
    logger.debug(f"Posting GitHub comment to {url}")
    try:
        resp = requests.post(url, headers=headers, json=payload)
        logger.debug(f"GitHub API responded: {resp.status_code} {resp.text}")
        if resp.status_code != 201:
            logger.error("Failed to post GitHub comment: %s", resp.status_code)
    except Exception as e:
        logger.exception("Exception while posting GitHub comment: %s", e)


def send_telegram(review: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": f"🔥 *AI Code Review*\n\n{review}", "parse_mode": "Markdown"}
    logger.debug(f"Sending Telegram message to {TELEGRAM_CHAT_ID}")
    try:
        resp = requests.post(url, json=data)
        logger.debug(f"Telegram API responded: {resp.status_code} {resp.text}")
        if resp.status_code != 200:
            logger.error("Failed to send Telegram message: %s", resp.status_code)
    except Exception as e:
        logger.exception("Exception while sending Telegram message: %s", e)


def main() -> None:
    logger.info("=== Starting AI code review script ===")
    try:
        diff = get_diff()
        if not diff.strip():
            logger.info("No changes detected, exiting")
            return
        review = review_code(diff)
        send_telegram(review)
        post_github_comment(review)
    except Exception as e:
        logger.exception("Unhandled exception in main: %s", e)
        exit(1)


if __name__ == "__main__":
    main()
