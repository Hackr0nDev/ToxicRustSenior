# .github/workflows/ai_review.py
import os
import requests
import subprocess
from openai import OpenAI

# === Конфигурация ProxyAPI ===
PROXYAPI_KEY = os.environ["PROXYAPI_KEY"]
PROXYAPI_URL = "https://api.proxyapi.ru/openai"
client = OpenAI(api_key=PROXYAPI_KEY, base_url=PROXYAPI_URL)

# === Прочие переменные ===
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4")
TELEGRAM_TOKEN  = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID= os.environ["TELEGRAM_CHAT_ID"]
GITHUB_TOKEN    = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO     = os.environ["GITHUB_REPOSITORY"]
PR_NUMBER       = os.environ.get("PR_NUMBER")
COMMIT_SHA      = os.environ["GITHUB_SHA"]

# Проверяем секреты
required = ["PROXYAPI_KEY","TELEGRAM_BOT_TOKEN","TELEGRAM_CHAT_ID","GITHUB_REPOSITORY","GITHUB_SHA"]
for name in required:
    if name not in os.environ:
        raise RuntimeError(f"{name} not set in secrets")

# Системный промпт
SYSTEM_PROMPT = """
Ты токсичный, высокомерный senior-разработчик, одержимый оптимизацией.
Формат:
Комментарий
```rs
<код>
```"""

# Функции
def get_diff() -> str:
    res = subprocess.run([
        "git","diff","HEAD~1","HEAD"
    ], stdout=subprocess.PIPE, text=True)
    return res.stdout

def review_code(diff: str) -> str:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role":"system","content":SYSTEM_PROMPT},
            {"role":"user","content":f"Вот diff кода:\n\n{diff}"}
        ],
        temperature=0.7
    )
    return resp.choices[0].message.content

def post_github_comment(body: str) -> None:
    if PR_NUMBER and GITHUB_TOKEN:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{PR_NUMBER}/comments"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        requests.post(url, headers=headers, json={"body": body})

def send_telegram(review: str) -> None:
    msg = f"🔥 *AI Code Review*\n\n{review}"
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    )

# Основная логика
def main() -> None:
    diff = get_diff()
    if not diff.strip():
        print("Нет изменений для ревью.")
        return
    review = review_code(diff)
    send_telegram(review)
    post_github_comment(review)

if __name__ == "__main__":
    main()
