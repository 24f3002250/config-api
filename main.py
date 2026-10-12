import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

ALIASES = {
    "NUM_WORKERS": "workers",
    "APP_PORT": "port",
    "APP_WORKERS": "workers",
    "APP_DEBUG": "debug",
    "APP_LOG_LEVEL": "log_level",
    "APP_API_KEY": "api_key",
}

def normalize_key(key):
    key = key.strip()
    return ALIASES.get(key, key.lower())

def to_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {
        "true", "1", "yes", "on"
    }

def coerce(key, value):
    if key in ("port", "workers"):
        return int(value)
    if key == "debug":
        return to_bool(value)
    return str(value)

@app.get("/")
def root():
    return {"message": "Config API is running"}

@app.get("/effective-config")
def effective_config(set: list[str] | None = Query(default=None)):
    config = DEFAULTS.copy()

    env_name = os.getenv("APP_ENV", "development")
    yaml_path = Path(f"config.{env_name}.yaml")

    if yaml_path.exists():
        with yaml_path.open() as f:
            yaml_config = yaml.safe_load(f) or {}
        for key, value in yaml_config.items():
            config[normalize_key(key)] = value

    for key, value in dotenv_values(".env").items():
        if value is not None:
            config[normalize_key(key)] = value

    for key, value in os.environ.items():
        if key.startswith("APP_"):
            config[normalize_key(key)] = value

    for item in set or []:
        if "=" in item:
            key, value = item.split("=", 1)
            config[normalize_key(key)] = value

    result = {
        key: coerce(key, config[key])
        for key in DEFAULTS
    }
    result["api_key"] = "****"
    return result
