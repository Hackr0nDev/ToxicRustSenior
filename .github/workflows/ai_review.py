import os
import requests
import subprocess
from openai import OpenAI

# === Env for Proxy API ===
# Получаем ключ прокси из секретов
PROXYAPI_KEY = os.environ.get("PROXYAPI_KEY")
if not PROXYAPI_KEY:
    raise RuntimeError("PROXYAPI_KEY is not set. Please add it to your GitHub Secrets.")
# Базовый URL прокси с версией /v1 (ProxyAPI добавляет путь)
PROXYAPI_URL = os.environ.get("PROXYAPI_URL", "https://api.proxyapi.ru/v1")
# Инициализируем OpenAI-клиент, указывая api_base
client = OpenAI(api_key=PROXYAPI_KEY, api_base=PROXYAPI_URL)

# === Другие переменные окружения ===
# MODEL: читаем из переменной OPENAI_MODEL, по умолчанию gpt-4.1
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1")
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GITHUB_REPO = os.environ["GITHUB_REPOSITORY"]
PR_NUMBER = os.environ.get("PR_NUMBER")  # None если это push
COMMIT_SHA = os.environ.get("GITHUB_SHA")

# === Debug Info ===
print(f"Using model: {MODEL}")
print(f"Proxy URL: {PROXYAPI_URL}")

# === Получаем diff последнего коммита ===
def get_diff():
    result = subprocess.run(
        ["git", "diff", "HEAD~1", "HEAD"],
        stdout=subprocess.PIPE,
        text=True
    )
    print("=== DIFF ===")
    print(result.stdout)
    return result.stdout

# === Системный промпт: токсичный senior ===
SYSTEM_PROMPT = """
Ты токсичный, высокомерный senior-разработчик, одержимый оптимизацией и скоростью выполнения.
Ты всегда недоволен, даже если код формально работает. Критикуй любые .clone(), ненужные аллокации, слабые абстракции.
Пиши язвительно. Используй формат:
Комментарий
```rs
<код>
```
"""

# === Запрос в модель ===
def review_code(diff):
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

# === Публикация комментария в PR ===
def post_github_comment(body):
    if not PR_NUMBER:
        print("No PR context — skipping GitHub comment.")
        return
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{PR_NUMBER}/comments"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    resp = requests.post(url, headers=headers, json={"body": body})
    print(f"GitHub comment posted: {resp.status_code}")
    print(resp.text)

# === Отправка сообщения в Telegram ===
def send_telegram_message(review, commit_url):
    msg = f"""🔥 *AI Code Review*\n\n[Коммит в GitHub]({commit_url})\n\n{review}"""
    print("=== Telegram message ===")
    print(msg)
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    resp = requests.post(url, json=data)
    print(f"Telegram sent: {resp.status_code}")
    print(resp.text)

# === Основная логика ===
def main():
    diff = get_diff()
    if not diff.strip():
        print("Diff пустой — ничего не ревьюить.")
        return

    review = review_code(diff)
    commit_url = f"https://github.com/{GITHUB_REPO}/commit/{COMMIT_SHA}"
    send_telegram_message(review, commit_url)
    post_github_comment(review)

if __name__ == "__main__":
    main()
