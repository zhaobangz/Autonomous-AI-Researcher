FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    MPLCONFIGDIR=/tmp/matplotlib
RUN pip install --no-cache-dir numpy pandas matplotlib scipy
RUN useradd --create-home --shell /usr/sbin/nologin sandbox
WORKDIR /code
USER sandbox
