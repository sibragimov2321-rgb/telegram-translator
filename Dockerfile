FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py kg_translation.py tm_translation.py ./
COPY data/kg_style_profile.json data/kg_slang_dictionary.json data/kg_style_references.json data/kg_translation_examples.json ./data/
COPY data/tm_style_profile.json data/tm_slang_dictionary.json data/tm_spelling_variants.json data/tm_style_references.json data/tm_translation_examples.json ./data/

CMD ["python", "bot.py"]
