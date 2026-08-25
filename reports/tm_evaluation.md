# Turkmen translation OLD → NEW evaluation

Model: `openai/gpt-5.4`
Cases: 50

## Automated summary

- Current errors: 0
- New errors: 0
- Current entity-safe: 50/50
- New entity-safe: 50/50
- Current average reference similarity: 0.796
- New average reference similarity: 0.8622
- New closer to curated reference: 25
- Current closer to curated reference: 8
- Current average latency: 2.095 s
- New average latency: 1.284 s

Reference similarity is only a regression signal; it does not prove linguistic quality by itself.

## Side-by-side cases

### 1. holdout-ru-211 — ru_to_tm / questions

SOURCE: ты сейчас дома

REFERENCE: sen hazir oyde

CURRENT: sen hazir oyde

NEW: sen hazir oyde

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 2. holdout-ru-213 — ru_to_tm / numbers

SOURCE: я через 10 минут приду

REFERENCE: 10 minutdan bararyn

CURRENT: men 10 minutdan gelerin

NEW: men 10 minutdan bararyn

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 3. holdout-ru-217 — ru_to_tm / requests

SOURCE: пусть немного подождет

REFERENCE: azajyk garassyn

CURRENT: biraz garassyn

NEW: azajyk garasyn

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 4. holdout-ru-223 — ru_to_tm / negative

SOURCE: пока не отправляй

REFERENCE: hazirlikce ugratma

CURRENT: hazirlikce ugratma

NEW: hazir ugratma

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 5. holdout-ru-225 — ru_to_tm / casual

SOURCE: я сам проверю

REFERENCE: ozum barlaryn

CURRENT: Ozum barlap gorerin

NEW: ozim barlaryn

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 6. holdout-ru-237 — ru_to_tm / slang

SOURCE: ничего не понял брат

REFERENCE: hic zat dusunmedim brat

CURRENT: hic zada dusunmedim brat

NEW: Hic zada dusunmedim brat

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 7. holdout-ru-239 — ru_to_tm / screenshots

SOURCE: сначала отправь скрин

REFERENCE: ilki skrin ugrat

CURRENT: bashda skrin iber

NEW: basda skrin ugrat

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 8. holdout-ru-241 — ru_to_tm / money

SOURCE: деньги вернутся на карту

REFERENCE: pul karta gaydyp geler

CURRENT: pul karta gaydyp geler

NEW: pul karta yza geler

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 9. holdout-ru-249 — ru_to_tm / Telegram

SOURCE: напиши @manager сейчас

REFERENCE: hazir @manager yaz

CURRENT: hazir @manager yaz

NEW: @manager hazir yaz

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 10. holdout-ru-263 — ru_to_tm / very_short

SOURCE: просто жди

REFERENCE: garas

CURRENT: diymek garas

NEW: diymek garas

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 11. holdout-ru-265 — ru_to_tm / promo

SOURCE: это твой промокод A7K92

REFERENCE: bu senin promokodyn A7K92

CURRENT: bu senin promokodyn A7K92

NEW: bu senin promokodyn A7K92

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 12. holdout-ru-269 — ru_to_tm / formal

SOURCE: пожалуйста не меняйте пароль

REFERENCE: hayys paroly uytgetman

CURRENT: hayys paroly uytgetman

NEW: Hayys paroly uytgetman

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 13. holdout-tm-212 — tm_to_ru / questions

SOURCE: sen hazir oyde

REFERENCE: ты сейчас дома

CURRENT: ты сейчас дома

NEW: ты сейчас дома

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 14. holdout-tm-214 — tm_to_ru / numbers

SOURCE: 10 minutdan bararyn

REFERENCE: я через 10 минут приду

CURRENT: Через 10 минут приду.

NEW: Через 10 минут приду

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 15. holdout-tm-218 — tm_to_ru / requests

SOURCE: azajyk garassyn

REFERENCE: пусть немного подождет

CURRENT: Пусть немного посмотрит.

NEW: подожди немного

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 16. holdout-tm-224 — tm_to_ru / negative

SOURCE: hazirlikce ugratma

REFERENCE: пока не отправляй

CURRENT: Не заставляй меня ждать.

NEW: Пока не отправляй

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 17. holdout-tm-226 — tm_to_ru / casual

SOURCE: ozum barlaryn

REFERENCE: я сам проверю

CURRENT: Я сам разберусь.

NEW: сам проверю

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 18. holdout-tm-238 — tm_to_ru / slang

SOURCE: hic zat dusunmedim brat

REFERENCE: ничего не понял брат

CURRENT: Я вообще ничего не понял, брат.

NEW: Я ничего не понял, брат.

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 19. holdout-tm-240 — tm_to_ru / screenshots

SOURCE: ilki skrin ugrat

REFERENCE: сначала отправь скрин

CURRENT: Сначала отправь скрин.

NEW: сначала скинь скрин

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 20. holdout-tm-242 — tm_to_ru / money

SOURCE: pul karta gaydyp geler

REFERENCE: деньги вернутся на карту

CURRENT: деньги вернутся на карту

NEW: деньги вернутся на карту

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 21. holdout-tm-250 — tm_to_ru / Telegram

SOURCE: hazir @manager yaz

REFERENCE: напиши @manager сейчас

CURRENT: готов, напиши @manager

NEW: сейчас напиши @manager

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 22. holdout-tm-264 — tm_to_ru / very_short

SOURCE: garas

REFERENCE: просто жди

CURRENT: Смотри.

NEW: подожди

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 23. holdout-tm-266 — tm_to_ru / promo

SOURCE: bu senin promokodyn A7K92

REFERENCE: это твой промокод A7K92

CURRENT: это твой промокод A7K92

NEW: это твой промокод A7K92

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 24. holdout-tm-270 — tm_to_ru / formal

SOURCE: hayys paroly uytgetman

REFERENCE: пожалуйста не меняйте пароль

CURRENT: нет, не меняй пароль

NEW: пожалуйста, не меняй пароль

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 25. holdout-ru-215 — ru_to_tm / questions

SOURCE: ему уже написал

REFERENCE: ona yazdynmy

CURRENT: ona artkacin yazdym

NEW: ona indi yazdym

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 26. holdout-ru-221 — ru_to_tm / requests

SOURCE: скинь номер карты

REFERENCE: karta nomerini ugrat

CURRENT: kart nomerini ugrat

NEW: kart nomerin ugrat

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 27. holdout-ru-227 — ru_to_tm / casual

SOURCE: потом поговорим

REFERENCE: son gurrun ederis

CURRENT: sonra gurseseris

NEW: son gurseseris

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 28. holdout-ru-229 — ru_to_tm / negative

SOURCE: ответ еще не пришел

REFERENCE: jogap entek gelenok

CURRENT: jogap entek gelmedi

NEW: jogap entek gelenok

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 29. holdout-ru-243 — ru_to_tm / money

SOURCE: с баланса сняли 8%

REFERENCE: balansdan 8% alyndy

CURRENT: balansdan 8% ayryldy

NEW: balansdan 8% aldylar

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 30. holdout-ru-247 — ru_to_tm / numbers

SOURCE: мой ID 483920

REFERENCE: menin ID im 483920

CURRENT: menin ID 483920

NEW: menin ID 483920

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 31. holdout-ru-251 — ru_to_tm / Telegram

SOURCE: открой https://t.me/example

REFERENCE: https://t.me/example ac

CURRENT: ac https://t.me/example

NEW: https://t.me/example ac

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 32. holdout-ru-255 — ru_to_tm / slang

SOURCE: ща уточню у него

REFERENCE: hazir ondan soraryn

CURRENT: hazir ondan anyklap bereyin

NEW: hazir ondan sorap anyklayyn

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 33. holdout-tm-216 — tm_to_ru / questions

SOURCE: ona yazdynmy

REFERENCE: ему уже написал

CURRENT: Ты ей написал?

NEW: Ты ему написал?

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 34. holdout-tm-222 — tm_to_ru / requests

SOURCE: karta nomerini ugrat

REFERENCE: скинь номер карты

CURRENT: Отправь номер карты

NEW: скинь номер карты

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 35. holdout-tm-228 — tm_to_ru / casual

SOURCE: son gurrun ederis

REFERENCE: потом поговорим

CURRENT: Поговорим потом

NEW: потом поговорим

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 36. holdout-tm-230 — tm_to_ru / negative

SOURCE: jogap entek gelenok

REFERENCE: ответ еще не пришел

CURRENT: Ответа ещё нет.

NEW: ответа еще нет

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 37. holdout-tm-244 — tm_to_ru / money

SOURCE: balansdan 8% alyndy

REFERENCE: с баланса сняли 8%

CURRENT: С баланса сняли 8%

NEW: С баланса сняли 8%

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 38. holdout-tm-248 — tm_to_ru / numbers

SOURCE: menin ID im 483920

REFERENCE: мой ID 483920

CURRENT: мой ID 483920

NEW: мой ID 483920

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 39. holdout-tm-252 — tm_to_ru / Telegram

SOURCE: https://t.me/example ac

REFERENCE: открой https://t.me/example

CURRENT: https://t.me/example ак

NEW: открой https://t.me/example

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 40. holdout-tm-256 — tm_to_ru / slang

SOURCE: hazir ondan soraryn

REFERENCE: ща уточню у него

CURRENT: Ладно, я у него спрошу.

NEW: сейчас у него спрошу

MEANING PRESERVED: no
STYLE: pass
ENTITY PRESERVATION: pass

### 41. holdout-ru-219 — ru_to_tm / questions

SOURCE: у тебя есть другая карта

REFERENCE: sende baska karta barmy

CURRENT: sende bashga karta barmy

NEW: sende basga karta barmy

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 42. holdout-ru-245 — ru_to_tm / money

SOURCE: отправь ровно 1200 TMT

REFERENCE: 1200 TMT ugrat

CURRENT: Takyk 1200 TMT ugrat

NEW: doly 1200 TMT ugrat

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 43. holdout-ru-253 — ru_to_tm / requests

SOURCE: завтра утром напомни

REFERENCE: ertir irden yatlat

CURRENT: ertir irden yadyma sal

NEW: ertir irden yadat

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 44. holdout-ru-257 — ru_to_tm / slang

SOURCE: да брат все нормально

REFERENCE: howwa brat hemme zat normal

CURRENT: howa brat hemmesi gowy

NEW: ha brat hemme zat normal

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 45. holdout-ru-259 — ru_to_tm / negative

SOURCE: не бери трубку

REFERENCE: telefony alma

CURRENT: trubkany alma

NEW: trubkany alma

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 46. holdout-tm-220 — tm_to_ru / questions

SOURCE: sende baska karta barmy

REFERENCE: у тебя есть другая карта

CURRENT: У тебя есть другая карта?

NEW: У тебя есть другая карта?

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 47. holdout-tm-246 — tm_to_ru / money

SOURCE: 1200 TMT ugrat

REFERENCE: отправь ровно 1200 TMT

CURRENT: Отправь 1200 TMT

NEW: скинь 1200 TMT

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 48. holdout-tm-254 — tm_to_ru / requests

SOURCE: ertir irden yatlat

REFERENCE: завтра утром напомни

CURRENT: Завтра утром уложу спать

NEW: завтра утром напомни

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 49. holdout-tm-258 — tm_to_ru / slang

SOURCE: howwa brat hemme zat normal

REFERENCE: да брат все нормально

CURRENT: ага брат, всё нормально

NEW: да брат всё нормально

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass

### 50. holdout-tm-260 — tm_to_ru / negative

SOURCE: telefony alma

REFERENCE: не бери трубку

CURRENT: Не бери телефон.

NEW: Не бери телефон

MEANING PRESERVED: yes
STYLE: pass
ENTITY PRESERVATION: pass
