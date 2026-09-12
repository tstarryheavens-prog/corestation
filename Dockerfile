FROM python:3-alpine

WORKDIR /app

# Copy app files
COPY server.py sync.py index.html style.css app.js /app/
COPY assets/ /app/assets/
COPY data/ /app/data/

EXPOSE 80

ENV PYTHONUNBUFFERED=1

CMD ["python3", "server.py", "80"]
