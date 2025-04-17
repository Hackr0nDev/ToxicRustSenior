# .github/workflows/ai_review.py
import os
import requests
import subprocess
from openai import OpenAI

# === Конфигурация ProxyAPI ===
# URL прокси жёстко прописан в коде — не нужен в секретах
PROXYAPI_URL = "https://api.proxyapi.ru/openai"
PROXYAPI_KEY = os.environ["PROXYAPI_KEY"]

# инициализация клиента
client = OpenAI(api_key=PROXYAPI_KEY, base_url=PROXYAPI_URL)

# === Прочие переменные ===
MODEL            = os.environ.get("OPENAI_MODEL", "gpt-4")
TELEGRAM_TOKEN   = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GITHUB_TOKEN     = os.environ.get("GITHUB_TOKEN")  # опционально для комментариев
GITHUB_REPO      = os.environ["GITHUB_REPOSITORY"]
PR_NUMBER        = os.environ.get("PR_NUMBER")
COMMIT_SHA       = os.environ["GITHUB_SHA"]

# проверка обязательных секретов (кроме URL)
for name in (
    "PROXYAPI_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "GITHUB_REPOSITORY",
    "GITHUB_SHA"
):
    if name not in os.environ:
        raise RuntimeError(f"{name} не задан в секретах GitHub")

SYSTEM_PROMPT = """
Ты токсичный, высокомерный senior-разработчик, одержимый оптимизацией.
Формат ответа:
Комментарий
```rs
<код>
```"""


def get_diff() -> str:
    res = subprocess.run(
        ["git","diff","HEAD~1","HEAD"],
        stdout=subprocess.PIPE, text=True
    )
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


# .github/workflows/review.yml
name: AI Code Review

on:
  push:
    branches: ["**"]
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install deps
        run: |
          pip install --upgrade pip
          pip install openai requests

      - name: Fetch history
        run: git fetch --unshallow

      - name: Run AI review
        run: python .github/workflows/ai_review.py
        env:
          PROXYAPI_KEY:       ${{ secrets.PROXYAPI_KEY }}
          # PROXYAPI_URL не нужен в секретах — прописан в коде
          OPENAI_MODEL:       ${{ secrets.OPENAI_MODEL }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID:   ${{ secrets.TELEGRAM_CHAT_ID }}
          GITHUB_TOKEN:       ${{ secrets.GITHUB_TOKEN }}
          GITHUB_REPOSITORY:  ${{ github.repository }}
          PR_NUMBER:          ${{ github.event.pull_request.number }}
          GITHUB_SHA:         ${{ github.sha }}
