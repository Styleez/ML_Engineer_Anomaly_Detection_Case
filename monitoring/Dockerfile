FROM prom/prometheus:latest as prometheus

FROM grafana/grafana:latest

# Copy Prometheus binary
COPY --from=prometheus /bin/prometheus /bin/prometheus
COPY --from=prometheus /bin/promtool /bin/promtool

# Copy Prometheus config
COPY prometheus/prometheus.yml /etc/prometheus/prometheus.yml

# Copy Grafana config
COPY grafana/provisioning/datasources /etc/grafana/provisioning/datasources
COPY grafana/provisioning/dashboards /etc/grafana/provisioning/dashboards
COPY grafana/dashboards /var/lib/grafana/dashboards

# Set up environment
ENV GF_SECURITY_ADMIN_USER=admin
ENV GF_SECURITY_ADMIN_PASSWORD=admin
ENV GF_USERS_ALLOW_SIGN_UP=false

# Expose ports
EXPOSE 9090 3000

# Start both services
COPY start.sh /start.sh
USER root
RUN chmod +x /start.sh
USER grafana

CMD ["/bin/sh", "/start.sh"]
