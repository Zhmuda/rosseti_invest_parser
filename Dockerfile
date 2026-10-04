FROM python:3.12-slim

WORKDIR /app
COPY parse_rosseti_ipr_orders.py /app/parse_rosseti_ipr_orders.py
COPY rosseti_source_monitor.py /app/rosseti_source_monitor.py

RUN useradd --create-home --uid 10001 monitor \
    && mkdir -p /app/data \
    && chown -R monitor:monitor /app

USER monitor
CMD ["python", "-u", "rosseti_source_monitor.py"]
