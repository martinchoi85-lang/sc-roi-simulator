"""Unit test for schema validation and korea configuration loading."""

import pytest
from pathlib import Path
from engine.schema import load_country_config, ConfigValidationError


def test_load_korea_config():
    root = Path(__file__).resolve().parent.parent
    korea_dir = root / "korea"
    config = load_country_config(korea_dir)

    assert config.country_name == "korea"
    assert "country" in config.values
    assert "houses" in config.values
    assert "tariff" in config.values
    assert "capex" in config.values
    assert "subsidy" in config.values
    assert "load" in config.values
    assert "equipment" in config.values

    # Check scenario axes
    axes = config.values["country"]["scenario_axes"]
    assert len(axes["house_models"]) == 3
    assert len(axes["heating_packages"]) == 2
    assert len(axes["ev_options"]) == 2
    assert len(axes["occupancy_rates"]) == 6
    assert len(axes["target_models"]) == 3
    assert len(axes["subsidy_options"]) == 2

    # Verify placeholder tracking
    assert config.has_placeholder is True
    assert config.placeholder_count >= 1
    # Check that placeholders contain subsidy placeholders
    assert any("subsidy" in p for p in config.placeholders)

