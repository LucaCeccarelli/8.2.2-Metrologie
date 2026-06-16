# Kibana Exports

Ce dossier contiendra les exports Kibana à importer pour retrouver les dashboards et data views.

## Procédure d'export (après déploiement)

Depuis Kibana : **Stack Management → Saved Objects → Export**

Sélectionner et exporter :
- Data Views : `app-logs-*` et `air-quality-*`
- Dashboards : `Developer Dashboard`, `Support Dashboard`, `Air Quality Dashboard`
- Visualisations associées

Sauvegarder les fichiers `.ndjson` ici.

## Procédure d'import (sur cluster vierge)

```bash
# Via l'API Kibana
curl -X POST "http://localhost:5601/api/saved_objects/_import?overwrite=true" \
  -H "kbn-xsrf: true" \
  --form file=@kibana/dashboards.ndjson
```

Ou via l'interface : **Stack Management → Saved Objects → Import**

## Data Views à créer manuellement

### 1. `app-logs-*`
- **Index pattern** : `app-logs-*`
- **Champ temporel** : `@timestamp`
- Champs clés : `level`, `request_id`, `http_method`, `http_path`, `http_status_code`, `duration_ms`, `action`, `app_message`

### 2. `air-quality-*`
- **Index pattern** : `air-quality-*`
- **Champ temporel** : `@timestamp`
- Champs clés : `pollutant`, `data_value`, `geo_place_name`, `measure`, `time_period`

## Recherches Kibana — App Logs

| Objectif | Requête KQL |
|---|---|
| Erreurs serveur (5xx) | `http_status_family : "5xx"` |
| Erreurs client (4xx) | `http_status_family : "4xx"` |
| Par route | `http_path : "/error"` |
| Par request_id | `request_id : "uuid-ici"` |
| Logs niveau ERROR | `level : "ERROR"` |
| Requêtes lentes (>200ms) | `duration_ms > 200` |
| Actions business | `action : "order_created"` |

## Recherches Kibana — Air Quality

| Objectif | Requête KQL |
|---|---|
| Filtre polluant + data_value | `pollutant : "Ozone (O3)" AND data_value > 10` |
| Fenêtre temporelle | Utiliser le sélecteur de temps Kibana : 2008–2014 |
| Lieu géographique | `geo_place_name : "Bronx"` |
| Pics de pollution | Trier par `data_value` décroissant |

## Dashboards

### Developer Dashboard
Questions auxquelles il répond :
- Où sont les erreurs ? → bar chart par `http_path` filtré sur 5xx
- Quand ont commencé les erreurs ? → timeline des erreurs
- Quelles routes sont concernées ? → table top routes en erreur
- Quels messages reviennent ? → top `app_message`
- Derniers événements récents → table de logs récents

### Support Dashboard
Questions auxquelles il répond :
- L'application fonctionne-t-elle ? → taux de succès (2xx/total)
- Y a-t-il beaucoup d'erreurs ? → compteur erreurs/heure
- Quelle est l'activité globale ? → volume de requêtes dans le temps
- Pas de jargon technique — libellés en langage naturel

### Air Quality Dashboard
Visualisations :
- Time-series `Average(data_value)` par polluant (Lens)
- Heatmap ou table comparaison période × polluant
- Contrôle Options list sur `geo_place_name`
