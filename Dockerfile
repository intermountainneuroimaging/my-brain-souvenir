FROM python:3.8-slim as base

ENV FLYWHEEL="/flywheel/v0"
WORKDIR ${FLYWHEEL}

#DEV install git
RUN apt-get update && apt-get install -y git && \
    pip install "poetry==1.1.13"

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-dev --no-root

COPY run.py manifest.json $FLYWHEEL/
COPY fw_gear_souvenir $FLYWHEEL/fw_gear_souvenir
#COPY curator $FLYWHEEL/curator
RUN poetry install --no-dev

# Configure entrypoint
RUN chmod a+x $FLYWHEEL/run.py
ENTRYPOINT ["poetry","run","python","/flywheel/v0/run.py"]