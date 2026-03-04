# Gridbert + Home Assistant Integration

Gridbert's REST API can be used as a data source for Home Assistant sensors.

## Prerequisites

1. Gridbert running (locally or cloud) with a user account
2. An API token (JWT from login endpoint)

## Getting Your API Token

```bash
# Register or login to get a JWT token
curl -s http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "your-password"}' \
  | jq -r .access_token
```

Save the token — it's valid for 24h (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`).

## Home Assistant Configuration

Add to your `configuration.yaml`:

```yaml
# Gridbert Energy Agent Integration
rest:
  - resource: http://localhost:8000/api/health
    scan_interval: 300  # 5 minutes
    headers:
      Authorization: !secret gridbert_token
    sensor:
      - name: "Gridbert Status"
        value_template: "{{ value_json.status }}"

# Chat with Gridbert via REST command
rest_command:
  gridbert_chat:
    url: "http://localhost:8000/api/chat"
    method: POST
    headers:
      Authorization: !secret gridbert_token
      Content-Type: "application/json"
    payload: '{"message": "{{ message }}"}'

# Dashboard Widgets as sensors
rest:
  - resource: http://localhost:8000/api/dashboard/widgets
    scan_interval: 3600  # 1 hour
    headers:
      Authorization: !secret gridbert_token
    sensor:
      - name: "Gridbert Widgets"
        value_template: "{{ value_json | length }}"
        json_attributes:
          - widget_type
          - config
```

Add to your `secrets.yaml`:

```yaml
gridbert_token: "Bearer eyJ..."
```

## Automation Example

Trigger Gridbert to check energy news every morning:

```yaml
automation:
  - alias: "Gridbert Morning Energy Check"
    trigger:
      platform: time
      at: "07:00:00"
    action:
      - service: rest_command.gridbert_chat
        data:
          message: "Gibt es Neuigkeiten zu Energiepreisen oder Förderungen?"
```

## Advanced: Custom Component

For deeper integration (real-time updates, conversation UI in HA), a custom component
is planned for Phase 5. The REST API above covers basic sensor data in the meantime.
