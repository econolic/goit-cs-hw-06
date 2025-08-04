FROM python:3.11-slim

# Встановлення робочої директорії
WORKDIR /app

# Копіювання файлів requirements
COPY requirements.txt .

# Встановлення залежностей
RUN pip install --no-cache-dir -r requirements.txt

# Копіювання коду додатку
COPY main.py .
COPY config.py .
COPY front-init ./front-init

# Відкриття портів
EXPOSE 3000 5000

# Запуск додатку
CMD ["python", "main.py"]
