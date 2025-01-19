# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.12-bullseye

EXPOSE 8050

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends curl

# Install Poetry
ENV POETRY_HOME="/opt/poetry"
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN curl -sSL https://install.python-poetry.org | python3 -

# Set the working directory inside the container
WORKDIR /app

# Copy the application code to the container
COPY ../ /app

# Configure Poetry to not create virtual environments
RUN poetry config virtualenvs.create false

# Install project dependencies
RUN poetry install --only main --no-interaction --no-ansi

# give execute permission to the startup script

# RUN chmod +x /app/startupScript.sh

# Set the entrypoint for the container
# ENTRYPOINT ["/app/startupScript.sh"]
