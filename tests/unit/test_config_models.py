import pytest
from pydantic import ValidationError

from app.config import Settings
from app.config.models import ModelSettings

VALID = {"model_backend": "ollama"}


@pytest.mark.parametrize(
    "invalid",
    [
        {"model_backend": "unknown"},
        {"generation_model": "qwen3:cloud"},
        {"embedding_model": " "},
        {"ollama_generation_url": "ftp://model"},
        {"ollama_query_embedding_url": "http://user:password@model"},
        {"model_context_tokens": 512, "model_max_output_tokens": 512},
        {"model_max_concurrency": 0},
    ],
)
def test_invalid_configuration_is_rejected(invalid):
    with pytest.raises(ValidationError):
        ModelSettings(_env_file=None, **invalid)


def test_valid_component_configuration_and_production_guards():
    ModelSettings(_env_file=None, **VALID)
    ModelSettings(_env_file=None, app_env="production", **VALID)
    with pytest.raises(ValidationError):
        ModelSettings(
            _env_file=None,
            app_env="production",
            **{**VALID, "model_backend": "fake"},
        )


def test_settings_composition_keeps_component_validation():
    Settings(_env_file=None, **VALID)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, model_backend="unknown")


def test_local_and_gpu_endpoints_share_the_same_settings_contract(monkeypatch):
    local = ModelSettings(_env_file=None)
    assert local.model_backend == "fake" and local.model_max_concurrency == 1
    monkeypatch.setenv("OLLAMA_GENERATION_URL", "https://gpu.internal:11434/")
    monkeypatch.setenv("MODEL_BACKEND", "ollama")
    deployed = ModelSettings(_env_file=None)
    assert deployed.ollama_generation_url == "https://gpu.internal:11434"
    assert deployed.generation_model == local.generation_model
    assert deployed.embedding_model == local.embedding_model
