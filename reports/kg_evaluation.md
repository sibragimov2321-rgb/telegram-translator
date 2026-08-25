# Kyrgyz translation OLD → NEW evaluation

Model: `openai/gpt-5.4`
Cases: 50

## Automated summary

- Current errors: 0
- New errors: 0
- Current entity-safe: 50/50
- New entity-safe: 50/50
- Current average reference similarity: 0.7881
- New average reference similarity: 0.8217
- New closer to curated reference: 20
- Current closer to curated reference: 11
- Current average latency: 1.638 s
- New average latency: 1.233 s

Reference similarity is only a regression signal; it does not prove linguistic quality by itself.

## Side-by-side cases

### 1. holdout-ky-001 — ky_to_ru / questions

SOURCE: азыр үйдөсүңбү?

REFERENCE: ты сейчас дома?

CURRENT: Ты сейчас дома?

NEW: ты сейчас дома?

### 2. holdout-ky-002 — ky_to_ru / numbers

SOURCE: 10 мүнөттөн кийин барам

REFERENCE: я через 10 минут приду

CURRENT: Через 10 минут пойду.

NEW: Через 10 минут приду

### 3. holdout-ky-004 — ky_to_ru / requests

SOURCE: бир аз күтүп турсун

REFERENCE: пусть подождет немного

CURRENT: Пусть немного подождёт.

NEW: пусть немного подождёт

### 4. holdout-ky-007 — ky_to_ru / negative_statements

SOURCE: азырынча жибербе

REFERENCE: не отправляй пока

CURRENT: пока не отправляй

NEW: пока не отправляй

### 5. holdout-ky-008 — ky_to_ru / casual

SOURCE: өзүм текшерем

REFERENCE: я сам проверю

CURRENT: Я сам проверю.

NEW: сам проверю

### 6. holdout-ky-013 — ky_to_ru / mixed_ru_ky

SOURCE: ал точно макулбу?

REFERENCE: он точно согласен?

CURRENT: Ал, точно подойдёт?

NEW: он точно согласен?

### 7. holdout-ky-014 — ky_to_ru / slang

SOURCE: эч нерсе түшүнгөн жокмун брат

REFERENCE: ничего не понял брат

CURRENT: Я вообще ничего не понял, брат.

NEW: Я вообще ничего не понял, брат.

### 8. holdout-ky-015 — ky_to_ru / screenshots

SOURCE: биринчи скрин жибер

REFERENCE: сначала отправь скрин

CURRENT: Отправь первый скрин.

NEW: сначала скинь скрин

### 9. holdout-ky-016 — ky_to_ru / money

SOURCE: акча картага кайра түшөт

REFERENCE: деньги вернутся на карту

CURRENT: деньги снова поступят на карту

NEW: деньги снова поступят на карту

### 10. holdout-ky-020 — ky_to_ru / Telegram

SOURCE: @manager ге азыр жаз

REFERENCE: напиши @manager сейчас

CURRENT: Напиши сейчас @manager

NEW: Сейчас напиши @manager-у

### 11. holdout-ky-027 — ky_to_ru / very_short

SOURCE: жөн эле күт

REFERENCE: просто жди

CURRENT: просто подожди

NEW: просто подожди

### 12. holdout-ky-030 — ky_to_ru / formal

SOURCE: парольду өзгөртпөй туруңузчу

REFERENCE: пожалуйста не меняйте пароль

CURRENT: Пожалуйста, пока не меняйте пароль.

NEW: Пока не меняйте пароль, пожалуйста.

### 13. holdout-ru-001 — ru_to_ky / questions

SOURCE: ты сейчас дома?

REFERENCE: азыр үйдөсүңбү?

CURRENT: Сен азыр үйдөсүңбү?

NEW: сен азыр үйдөсүңбү?

### 14. holdout-ru-002 — ru_to_ky / numbers

SOURCE: я через 10 минут приду

REFERENCE: 10 мүнөттөн кийин барам

CURRENT: Мен 10 мүнөттөн кийин келем.

NEW: 10 мүнөттөн кийин келем

### 15. holdout-ru-004 — ru_to_ky / requests

SOURCE: пусть подождет немного

REFERENCE: бир аз күтүп турсун

CURRENT: Бир аз күтүп турсун.

NEW: бир аз күтүп турсун

### 16. holdout-ru-007 — ru_to_ky / negative_statements

SOURCE: не отправляй пока

REFERENCE: азырынча жибербе

CURRENT: Азырынча жибербе

NEW: Азырынча жөнөтпө

### 17. holdout-ru-008 — ru_to_ky / casual

SOURCE: я сам проверю

REFERENCE: өзүм текшерем

CURRENT: өзүм текшерем

NEW: өзүм текшерем

### 18. holdout-ru-013 — ru_to_ky / mixed_ru_ky

SOURCE: он точно согласен?

REFERENCE: ал точно макулбу?

CURRENT: Ал так макулбу?

NEW: ал точно макулбу?

### 19. holdout-ru-014 — ru_to_ky / slang

SOURCE: ничего не понял брат

REFERENCE: эч нерсе түшүнгөн жокмун брат

CURRENT: Эч нерсе түшүнгөн жокмун, брат.

NEW: Эч нерсе түшүнгөн жокмун брат

### 20. holdout-ru-015 — ru_to_ky / screenshots

SOURCE: сначала отправь скрин

REFERENCE: биринчи скрин жибер

CURRENT: Адегенде скринди жибер.

NEW: биринчи скрин жиберчи

### 21. holdout-ru-016 — ru_to_ky / money

SOURCE: деньги вернутся на карту

REFERENCE: акча картага кайра түшөт

CURRENT: акча картага кайтып келет

NEW: акча картага кайтып келет

### 22. holdout-ru-020 — ru_to_ky / Telegram

SOURCE: напиши @manager сейчас

REFERENCE: @manager ге азыр жаз

CURRENT: азыр @manager'ге жазчы

NEW: @managerге азыр жаз

### 23. holdout-ru-027 — ru_to_ky / very_short

SOURCE: просто жди

REFERENCE: жөн эле күт

CURRENT: жөн эле күт

NEW: жөн эле күтүп тур

### 24. holdout-ru-030 — ru_to_ky / formal

SOURCE: пожалуйста не меняйте пароль

REFERENCE: парольду өзгөртпөй туруңузчу

CURRENT: Сураныч, сырсөздү алмаштырбаңыз.

NEW: Сураныч паролду өзгөртпөңүз

### 25. holdout-ky-003 — ky_to_ru / questions

SOURCE: ага жаздыңбы?

REFERENCE: ему уже написал?

CURRENT: ага, ты написал?

NEW: Ты ему написал?

### 26. holdout-ky-006 — ky_to_ru / requests

SOURCE: карта номерин жиберчи

REFERENCE: скинь номер карты

CURRENT: Скинь номер карты.

NEW: Скинь пожалуйста номер карты

### 27. holdout-ky-009 — ky_to_ru / casual

SOURCE: кийин сүйлөшөбүз

REFERENCE: потом созвонимся

CURRENT: Потом поговорим.

NEW: потом поговорим

### 28. holdout-ky-010 — ky_to_ru / negative_statements

SOURCE: жооп али келе элек

REFERENCE: ответ пока не пришел

CURRENT: Ответа пока ещё не было.

NEW: ответа еще не было

### 29. holdout-ky-017 — ky_to_ru / money

SOURCE: баланстан 8% алышты

REFERENCE: с баланса сняли 8%

CURRENT: С баланса сняли 8%

NEW: С баланса сняли 8%

### 30. holdout-ky-019 — ky_to_ru / numbers

SOURCE: менин ID 483920

REFERENCE: мой ID 483920

CURRENT: мой ID 483920

NEW: мой ID 483920

### 31. holdout-ky-021 — ky_to_ru / Telegram

SOURCE: https://t.me/example ач

REFERENCE: открой https://t.me/example

CURRENT: https://t.me/example открой

NEW: открой https://t.me/example

### 32. holdout-ky-023 — ky_to_ru / slang

SOURCE: азыр андан тактап алам

REFERENCE: ща уточню у него

CURRENT: Сейчас у него уточню.

NEW: сейчас у него уточню

### 33. holdout-ru-003 — ru_to_ky / questions

SOURCE: ему уже написал?

REFERENCE: ага жаздыңбы?

CURRENT: Ага жазып койдуңбу?

NEW: ага жаздыңбы эми?

### 34. holdout-ru-006 — ru_to_ky / requests

SOURCE: скинь номер карты

REFERENCE: карта номерин жиберчи

CURRENT: Картаңдын номерин жиберчи

NEW: картанын номерин жиберчи

### 35. holdout-ru-009 — ru_to_ky / casual

SOURCE: потом созвонимся

REFERENCE: кийин сүйлөшөбүз

CURRENT: анан чалышып сүйлөшөбүз

NEW: кийин чалышабыз

### 36. holdout-ru-010 — ru_to_ky / negative_statements

SOURCE: ответ пока не пришел

REFERENCE: жооп али келе элек

CURRENT: жооп азырынча келген жок

NEW: жооп азырынча келе элек

### 37. holdout-ru-017 — ru_to_ky / money

SOURCE: с баланса сняли 8%

REFERENCE: баланстан 8% алышты

CURRENT: Баланстан 8% алып салышты

NEW: баланстан 8% алып салышты

### 38. holdout-ru-019 — ru_to_ky / numbers

SOURCE: мой ID 483920

REFERENCE: менин ID 483920

CURRENT: менин ID'м 483920

NEW: менин IDм 483920

### 39. holdout-ru-021 — ru_to_ky / Telegram

SOURCE: открой https://t.me/example

REFERENCE: https://t.me/example ач

CURRENT: https://t.me/example ачып көрчү

NEW: https://t.me/example ач

### 40. holdout-ru-023 — ru_to_ky / slang

SOURCE: ща уточню у него

REFERENCE: азыр андан тактап алам

CURRENT: Азыр андан тактап алам

NEW: азыр андан тактап коёюн

### 41. holdout-ky-005 — ky_to_ru / questions

SOURCE: башка картаң барбы?

REFERENCE: у тебя есть другая карта?

CURRENT: Есть другая карта?

NEW: другая карта есть?

### 42. holdout-ky-018 — ky_to_ru / money

SOURCE: точно 1200 сом жибер

REFERENCE: отправь ровно 1200 сом

CURRENT: точно отправь 1200 сом

NEW: точно скинь 1200 сом

### 43. holdout-ky-022 — ky_to_ru / requests

SOURCE: эртең менен эскертип кой

REFERENCE: завтра утром напомни

CURRENT: Утром напомни.

NEW: Утром напомни.

### 44. holdout-ky-024 — ky_to_ru / slang

SOURCE: ооба брат баары норм

REFERENCE: да брат все четко

CURRENT: ага, брат, всё норм

NEW: да брат, всё норм

### 45. holdout-ky-025 — ky_to_ru / negative_statements

SOURCE: трубканы алба

REFERENCE: не бери трубку

CURRENT: Не бери трубку.

NEW: не бери трубку

### 46. holdout-ky-028 — ky_to_ru / Telegram

SOURCE: бул сенин промокодуң A7K92

REFERENCE: это твой промокод A7K92

CURRENT: это твой промокод A7K92

NEW: это твой промокод A7K92

### 47. holdout-ru-005 — ru_to_ky / questions

SOURCE: у тебя есть другая карта?

REFERENCE: башка картаң барбы?

CURRENT: сенде башка карта барбы?

NEW: сенде башка карта барбы?

### 48. holdout-ru-018 — ru_to_ky / money

SOURCE: отправь ровно 1200 сом

REFERENCE: точно 1200 сом жибер

CURRENT: так 1200 сом жөнөт

NEW: так 1200 сом жибер

### 49. holdout-ru-022 — ru_to_ky / requests

SOURCE: завтра утром напомни

REFERENCE: эртең менен эскертип кой

CURRENT: эртең эртең менен эскертип кой

NEW: эртең эртең менен эстетип кой

### 50. holdout-ru-024 — ru_to_ky / slang

SOURCE: да брат все четко

REFERENCE: ооба брат баары норм

CURRENT: Ооба, брат, баары жайында.

NEW: ооба брат баары так
