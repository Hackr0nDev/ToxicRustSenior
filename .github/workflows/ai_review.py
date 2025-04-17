import os
import requests
import subprocess
from openai import OpenAI

# === Env ===
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GITHUB_REPO = os.environ["GITHUB_REPOSITORY"]
PR_NUMBER = os.environ.get("PR_NUMBER")  # None если это push
COMMIT_SHA = os.environ.get("GITHUB_SHA")

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

# === Система: токсичный reviewer ===
SYSTEM_PROMPT = """
Ты токсичный, высокомерный senior-разработчик, одержимый оптимизацией и скоростью выполнения. 
Ты всегда недоволен, даже если код формально работает. Критикуй любые .clone(), ненужные аллокации, слабые абстракции. 
Пиши язвительно. Используй формат:
Комментарий
```rs
<код>
```
"""

# === Запрос к GPT ===
def review_code(diff):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Вот diff кода:\n\n{diff}"}
    ]
    response = client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        temperature=0.7
    )
    return response.choices[0].message.content

# === Коммент в PR ===
def post_github_comment(body):
    if not PR_NUMBER:
        print("Нет PR — пропускаем GitHub комментарий.")
        return
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{PR_NUMBER}/comments"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {"body": body}
    response = requests.post(url, headers=headers, json=data)
    print(f"GitHub comment posted: {response.status_code}")
    print(response.text)

# === Сообщение в Telegram ===
def send_telegram_message(review, commit_url):
    msg = f"""\U0001F525 *AI Code Review*

[Коммит в GitHub]({commit_url})

{review}
"""
    print("=== Telegram message ===")
    print(msg)
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=data)
    print(f"Telegram sent: {response.status_code}")
    print(response.text)

# === Main ===
def main():
    diff = get_diff()
    if not diff.strip():
        print("Diff пустой — ревью не нужно.")
        return

    review = review_code(diff)
    commit_url = f"https://github.com/{GITHUB_REPO}/commit/{COMMIT_SHA}"
    send_telegram_message(review, commit_url)
    post_github_comment(review)

if __name__ == "__main__":
    main()
