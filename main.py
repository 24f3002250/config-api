
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

BASE_DIR = Path(__file__).resolve().parent

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

ALIASES = {
    "num_workers": "workers",
    "app_port": "port",
    "app_workers": "workers",
    "app_debug": "debug",
    "app_log_level": "log_level",
    "app_api_key": "api_key",
}

def normalize_key(key):
    key = key.strip().lower()
    return ALIASES.get(key, key)

def coerce(key, value):
    if key in ("port", "workers"):
        return int(value)
    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in (
            "true", "1", "yes", "on"
        )
    return str(value)

@app.get("/")
def root():
    return {"message": "Config API is running"}

@app.get("/effective-config")
def effective_config(set: list[str] | None = Query(default=None)):
    config = DEFAULTS.copy()

    # 1. Environment-specific YAML
    env_name = os.environ.get("APP_ENV", "development")
    yaml_path = BASE_DIR / f"config.{env_name}.yaml"

    if yaml_path.exists():
        with yaml_path.open() as f:
            yaml_config = yaml.safe_load(f) or {}

        for key, value in yaml_config.items():
            key = normalize_key(key)
            if key in config:
                config[key] = coerce(key, value)

    # 2. .env file
    env_file = dotenv_values(BASE_DIR / ".env")

    for key, value in env_file.items():
        if value is not None:
            key = normalize_key(key)
            if key in config:
                config[key] = coerce(key, value)

    # 3. OS-level APP_* variables
    for env_key, value in os.environ.items():
        if env_key.startswith("APP_"):
            key = normalize_key(env_key)
            if key in config:
                config[key] = coerce(key, value)

    # 4. CLI query overrides
    for item in set or []:
        if "=" not in item:
            continue

        key, value = item.split("=", 1)
        key = normalize_key(key)

        if key in config:
            config[key] = coerce(key, value)

    # Always mask the secret
    config["api_key"] = "****"

    return config
