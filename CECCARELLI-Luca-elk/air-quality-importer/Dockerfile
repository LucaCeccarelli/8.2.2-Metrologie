FROM docker.elastic.co/logstash/logstash:8.19.16

# Remove default pipeline config
RUN rm -f /usr/share/logstash/pipeline/logstash.conf

# Copy our Air Quality import pipeline
COPY pipeline/logstash.conf /usr/share/logstash/pipeline/logstash.conf

# Disable xpack monitoring to avoid noise
ENV XPACK_MONITORING_ENABLED=false
