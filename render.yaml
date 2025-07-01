services:
  - type: web
    name: noobie-ide
    env: python
    buildCommand: "pip install --upgrade pip && pip install -r requirements.txt"
    startCommand: "gunicorn app:app"
    plan: free
    envVars:
      - key: FLASK_ENV
        value: production
      - key: POETRY_VERSION
        value: none
