# Art data server image: Flask (gunicorn) + a background job worker.
FROM python:3.9-slim
WORKDIR /app

# Data contract — mounted at runtime, NOT baked into the image (see docker_run.sh):
#   /app/LOCALDB        -> knowledgebase.db + images (+ comics.db)
#   /app/generated_maps -> canonical + demo maps, and the job-result cache
# The app creates /app/generated_maps at runtime if it is missing.

# Dependencies (PyTorch from the CPU wheel index)
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install --default-timeout=100 --retries=5 \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        -r requirements.txt

# Application code
COPY app/bootstrap.sh .
COPY app/gunicorn_config.py .
COPY app/voronoi_helper_functions.py .
COPY app/helper_functions helper_functions/
COPY app/index.py .
COPY app/templates/ templates/
COPY app/static/ static/
COPY app/config.py .

# Background job system (async map generation; queue in a local sqlite jobs.db)
COPY app/jobs/__init__.py jobs/
COPY app/jobs/map_job_processor.py jobs/
COPY app/jobs/schema.sql jobs/
COPY app/jobs/worker.py jobs/

RUN chmod +x bootstrap.sh

EXPOSE 8080
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["/bin/bash", "/app/bootstrap.sh"]
