FROM python:3.12-slim

WORKDIR /app

# 系统依赖（libpq for psycopg2, gcc for cffi）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码
COPY . .

# 日志目录
RUN mkdir -p logs

EXPOSE 8000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "main:app"]
