FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		ca-certificates \
		gcc \
		libsqlite3-dev \
	&& rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
	&& pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

RUN useradd --create-home --shell /bin/bash botuser \
	&& chown -R botuser:botuser /app

USER botuser

CMD ["python", "-u", "main.py"]

