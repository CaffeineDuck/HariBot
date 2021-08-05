FROM python:3.9.5-slim-buster

ARG YOUR_ENV

ENV YOUR_ENV=${YOUR_ENV} \
  PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 

# System deps:
RUN pip install poetry

# Copy only requirements to cache them in docker layer
WORKDIR /bot
COPY poetry.lock pyproject.toml /bot/

# Project initialization:
RUN poetry config virtualenvs.create false \
  && poetry install $(test "$YOUR_ENV" == production && echo "--no-dev") --no-interaction --no-ansi

# Creating folders, and files for a project:
COPY . /code

CMD aerich init -t bot.core.tortoise_config.tortoise_config\
    && aerich init-db\
    && aerich migrate\
    && aerich upgrade\
    && python -m bot