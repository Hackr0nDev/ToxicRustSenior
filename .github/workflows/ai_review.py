import os
import requests
import subprocess
from openai import OpenAI

# === Env for Proxy API ===
PROXYAPI_KEY = os.environ.get("PROXYAPI_KEY")
if not PROXYAPI_KEY:
    raise RuntimeError("PROXYAPI_KEY is not set. Please add it to your GitHub Secrets.")

# Получаем произвольный URL прокси (может включать /v1, /openai)
raw_url = os.environ.get("PROXYAPI_URL")
if not raw_url:
    raise RuntimeError("PROXYAPI_URL is not set. Please add it to your GitHub Secrets.")

# Нормализуем: убираем конечный слеш
url = raw_url.rstrip("/")
# Убираем любые конечные сегменты /v1 или /openai, чтобы не было дублирования
for suffix in ("/v1/openai", "/openai/v1", "/v1", "/openai"):  # порядок важен
    if url.endswith(suffix):
        url = url[: -len(suffix)]
        url = url.rstrip("/")
        break
# Формируем корректный базовый URL: провайдер openai идет первым, затем версия добавится клиентом
PROXYAPI_URL = url + "/openai"

# Инициализируем OpenAI-клиент с указанным base_url
client = OpenAI(api_key=PROXYAPI_KEY, base_url=PROXYAPI_URL)

# === Другие переменные окружения ===
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY")
PR_NUMBER = os.environ.get("PR_NUMBER")  # None если это push
COMMIT_SHA = os.environ.get("GITHUB_SHA")

# Проверяем обязательные переменные
required = {
    "GITHUB_TOKEN": GITHUB_TOKEN,
    "TELEGRAM_TOKEN": TELEGRAM_TOKEN,
    "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID,
    "GITHUB_REPOSITORY": GITHUB_REPO,
    "COMMIT_SHA": COMMIT_SHA
}
for name, value in required.items():
    if not value:
        raise RuntimeError(f"{name} is not set. Please add it to your GitHub Secrets.")

# === Debug Info ===
print(f"Using model: {MODEL}")
print(f"Proxy URL: {PROXYAPI_URL}")

# === Получаем diff последнего коммита ===
def get_diff() -> str:
    result = subprocess.run(
        ["git", "diff", "HEAD~1", "HEAD"],
        stdout=subprocess.PIPE,
        text=True
    )
    print("=== DIFF ===")
    print(result.stdout)
    return result.stdout

# === Системный промпт для ревьюера ===
SYSTEM_PROMPT = """
Ты токсичный, высокомерный senior-разработчик, одержимый оптимизацией и скоростью выполнения.
Ты всегда недоволен даже если код работает. Критикуй любые .clone(), лишние аллокации и слабые абстракции.
Пиши язвительно. Формат ответа:
Комментарий
```rs
<код>
```
"""

# === Запрос к модели ===
def review_code(diff: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Вот diff кода:\n\n{diff}"}
    ]
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.7
    )
    return response.choices[0].message.content

# === Публикация комментария в GitHub ===
def post_github_comment(body: str) -> None:
    if not PR_NUMBER:
        print("No PR context — пропускаем публикацию в GitHub.")
        return
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{PR_NUMBER}/comments"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    resp = requests.post(url, headers=headers, json={"body": body})
    print(f"GitHub comment status: {resp.status_code}")

# === Отправка в Telegram ===
def send_telegram_message(review: str, commit_url: str) -> None:
    msg = f"🔥 *AI Code Review*\n\n[Коммит в GitHub]({commit_url})\n\n{review}"
    print("=== Telegram message ===")
    print(msg)
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    resp = requests.post(url, json=data)
    print(f"Telegram send status: {resp.status_code}")

# === Основная логика ===
def main() -> None:
    diff = get_diff()
    if not diff.strip():
        print("Diff пустой — нечего ревьюить.")
        return

    review = review_code(diff)
    commit_url = f"https://github.com/{GITHUB_REPO}/commit/{COMMIT_SHA}"
    send_telegram_message(review, commit_url)
    post_github_comment(review)

if __name__ == "__main__":
    main()
