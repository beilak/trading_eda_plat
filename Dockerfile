FROM python:3.12-slim

WORKDIR /app

RUN pip3 install poetry

COPY poetry.lock pyproject.toml ./
COPY eda_platform eda_platform

RUN poetry config virtualenvs.in-project true

RUN poetry install --only main

EXPOSE 8081

ENTRYPOINT ["poetry", "run", "streamlit", "run", "eda_platform/main.py", "--server.port=8080", "--server.address=0.0.0.0"]