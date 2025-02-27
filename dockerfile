FROM python:3.9

WORKDIR /app

COPY . /app

ENV PYTHONPATH=/app

RUN pip install -r requirements.txt

CMD ["python", "-m", "bot.main"]
