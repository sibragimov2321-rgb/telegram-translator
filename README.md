# Telegram Business private translator

This bot is designed for fast conversations with foreign-language customers:

1. A customer sends a message to your connected Telegram Business account.
2. The bot sends you a private Russian translation in its own chat, with an
   **Answer in Russian** button.
3. You click the button and type an answer in Russian.
4. The bot translates the answer into the customer's detected language and sends
   it from your Business account.

The customer never sees the internal Russian translation or your Russian draft.
The Bot API cannot replace a message before Telegram sends it, so this private
inbox flow is the fastest way to keep the customer chat clean.

## Setup

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy its token.
2. Create an API key at [OpenRouter](https://openrouter.ai/settings/keys).
3. Copy `.env.example` to `.env`, then insert both keys.
4. Run in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python bot.py
```

5. Open the bot in Telegram and press **Start**.
6. In Telegram open **Settings → Telegram Business → Chatbots**, connect this
   bot, grant it access to read and send messages, and choose the private chats
   it may handle. If BotFather displays a Business mode setting, enable it.

Keep `.env` private. Do not commit it or send its contents to anyone.

## Постоянный запуск на Railway

1. Создайте проект и сервис из этого репозитория в Railway.
2. В разделе **Variables** добавьте значения из вашего локального `.env`:
   `TELEGRAM_BOT_TOKEN`, `OPENROUTER_API_KEY`, `TRANSLATION_MODEL`.
   Recommended model: `openai/gpt-4.1-mini`.
3. Добавьте также `DATABASE_PATH=/data/translator.sqlite3`.
4. В разделе **Volumes** создайте том и укажите путь подключения `/data`.
5. Railway сам обнаружит `Dockerfile`, соберёт проект и будет запускать `python bot.py` постоянно.

Ключи нельзя добавлять в GitHub или в файлы проекта. В Railway они хранятся в Variables.

Если `OPENROUTER_API_KEY` не задан, бот продолжит использовать `OPENAI_API_KEY`
как резервный вариант. Для OpenRouter адрес API выбирается автоматически.

## Разговорный кыргызский режим

Для изолированного разговорного перевода Russian ↔ Kyrgyz добавьте в Railway:

```env
KYRGYZ_CONVERSATIONAL_MODE=true
```

При `false` бот мгновенно возвращается к прежнему переводчику. Режим использует
только небольшие анонимные файлы из `data/`: профиль стиля, словарь-подсказку,
curated-примеры и до 6 подходящих стилевых сообщений. Исходный Telegram export
`result1.json` не входит в приложение, не загружается на Railway и не отправляется
в AI API.

Для повторной офлайн-сборки корпуса:

```powershell
python tools/build_kg_style_corpus.py C:\path\to\result1.json --output-dir data
python tools/build_kg_test_cases.py
```

Для сравнения 50 переводов старого и нового режимов (использует API и расходует
небольшое количество баланса):

```powershell
python tools/evaluate_kg_translation.py --limit 50
```

## Разговорный туркменский режим

Turkmen V1 изолирован от кыргызского и остальных языков. Для включения добавьте
в Railway:

```env
TM_CONVERSATIONAL_MODE=true
TM_OUTPUT_STYLE=tm_ascii_chat
```

`tm_ascii_chat` всегда выдаёт обычную латиницу без туркменских букв с диакритикой,
сохраняет знаки исходного сообщения и не придумывает лишнюю пунктуацию. `tm_native` разрешает стандартные буквы, а `chat_native`
выбирает стиль по формальности сообщения. При `TM_CONVERSATIONAL_MODE=false`
используется прежний переводчик.

Исходный Telegram export обрабатывается только локально и не входит в Docker-образ:

```powershell
python tools/build_tm_style_corpus.py "C:\path\to\result (туркмен.json" --output-dir data
python tools/build_tm_test_cases.py
python tools/evaluate_tm_translation.py --limit 50
```

## Notes

- Telegram allows one connected Business bot per account.
- The bot handles text messages. Voice messages, photos, and documents can be
  added next.
- Pending replies are stored in memory. A restart clears them; production use
  should store them in Redis or a database.
