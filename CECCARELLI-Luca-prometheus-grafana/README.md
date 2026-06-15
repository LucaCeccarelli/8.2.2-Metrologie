# TP Prometheus et Grafana - Luca CECCARELLI

## 1) Procedure de deploiement
```bash
# Creation du cluster local kind
kind create cluster --config kind-cluster.yaml

# Build de l'image applicative
docker build -t tpmetrics-app:v1.0.0 ./app

# Injection de l'image dans kind
kind load docker-image tpmetrics-app:v1.0.0 --name tp-observability

# Deploiement des manifests Kubernetes
kubectl apply -f manifests/
```

Verifier les pods:

```bash
kubectl get pods -A
kubectl get svc -A
```

## 2) Procedure d'acces aux interfaces

Les acces externes sont exposes via `NodePort` + `kind extraPortMappings`.

### Application

- URL directe via kind port mapping: `http://localhost:8080`
- Endpoints utiles:
  - `GET /ok` -> 2xx
  - `GET /not-found` -> 4xx
  - `GET /error` -> 5xx
  - `POST /process?items=30&delay_ms=150` -> metrique metier
  - `GET /metrics` -> metriques Prometheus

### Prometheus

Ouvrir `http://localhost:9090`.

### Alertmanager

Ouvrir `http://localhost:9093`.

### Grafana

Ouvrir `http://localhost:3000` avec:

- login: `admin`
- mot de passe: `admin`

## 3) Methode de generation de trafic

Script reproductible fourni:

```bash
./generate-traffic.sh
```

Ou avec URL explicite:

```bash
./generate-traffic.sh http://localhost:8080
```

Ce script genere:

- trafic `2xx`
- trafic `4xx`
- trafic `5xx`
- appels metier sur `/process` pour alimenter la metrique applicative

## 4) Choix d'instrumentation de l'application

L'application FastAPI expose:

- `app_http_requests_total{method,path,status_code,status_family}`
  - compteur HTTP par route et famille de code (`2xx/4xx/5xx`)
- `app_http_request_duration_seconds{method,path,status_family}`
  - histogramme de latence HTTP
- `app_processed_items_total`
  - metrique metier: nombre total d'items traites
- `app_in_progress_jobs`
  - jauge technique: jobs en cours

Instrumentation effectuee via middleware FastAPI et endpoint `/metrics`.

## 5) Requetes PromQL principales

Dashboard:

- Panel A (5xx sur 5 min):
  - `sum(increase(app_http_requests_total{status_family="5xx"}[5m]))`
- Panel B (4xx/5xx sur 5 min):
  - `sum by (status_family) (increase(app_http_requests_total{status_family=~"4xx|5xx"}[5m]))`
- Panel C (ligne trafic HTTP):
  - `sum by (status_family) (rate(app_http_requests_total{status_family=~"2xx|4xx|5xx"}[1m]))`
- Panel D (camembert repartition):
  - `sum by (status_family) (increase(app_http_requests_total{status_family=~"2xx|4xx|5xx"}[5m]))`
- Panel E (metrique applicative):
  - `sum(increase(app_processed_items_total[5m]))`

Alertes:

- Alerte 1 (indisponibilite composant obligatoire via collecte Prometheus):
  - expression basee sur `up{job="kubernetes-pods", component="..."}` + `absent(...)`
- Alerte 2 (trop d'erreurs 5xx):
  - `sum(increase(app_http_requests_total{status_family="5xx"}[5m])) > 20`
- Alerte 3 (Alertmanager indisponible dans Kubernetes):
  - `kube_deployment_status_replicas_available{namespace="monitoring", deployment="alertmanager"} < 1`
- Alerte 4 (alerte metier applicative):
  - `sum(increase(app_processed_items_total[5m])) > 200`

## 6) Seuil X choisi pour l'alerte 5xx

- Seuil retenu: `X = 20` erreurs `5xx` sur 5 minutes.
- Justification: en contexte de microservice simple, depasser 20 erreurs `5xx` sur 5 minutes indique une degradation significative, tout en evitant un bruit excessif lors d'incidents ponctuels tres courts.

## 7) Methode de test des alertes

### Test alerte 5xx

1. Executer `./generate-traffic.sh`.
2. Verifier que la requete des `5xx` depasse le seuil dans Prometheus.
3. Confirmer le passage de l'alerte `HighHttp5xxRate` a `Firing`.

### Test alerte indisponibilite d'un composant obligatoire

Exemple Grafana:

```bash
kubectl -n monitoring scale deployment grafana --replicas=0
```

Attendre ~1-2 minutes, puis verifier l'alerte `GrafanaTargetUnavailable`.

### Test alerte Alertmanager indisponible dans Kubernetes

```bash
kubectl -n monitoring scale deployment alertmanager --replicas=0
```

Attendre ~1-2 minutes, puis verifier l'alerte `AlertmanagerUnavailableInKubernetes`.

### Test alerte propre application

Executer:

```bash
for i in {1..10}; do curl -s -X POST "http://localhost:8080/process?items=30&delay_ms=100" > /dev/null; done
```

Puis verifier l'alerte `HighBusinessLoad`.

## 11) Hypotheses et limites

- Deploiement cible: cluster local `kind` mono-noeud.
- Alertmanager utilise un receveur minimal (pas d'integration e-mail/Slack) pour rester autonome et reproductible.
- Persistance longue duree (volumes dedies) non configuree pour Prometheus/Grafana.
- Le dashboard est fourni en export JSON dans `grafana/dashboard.json` et egalement provisionne via ConfigMap.
