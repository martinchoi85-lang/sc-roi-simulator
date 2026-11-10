"""Schema definition and configuration loader with strict metadata validation.

Every configuration parameter must have:
- value: The actual numerical, string, or boolean value
- unit: Physical or economic unit (e.g., 'm2', 'kW', 'KRW/kWh', 'none', 'fraction')
- source: Reference document, standard, or data origin
- grade: Confidence grade ('A': Official spec/code, 'B': Research/peer-reviewed, 'C': Assumption/heuristic)
- status: Data status ('VERIFIED', 'UNVERIFIED', or 'PLACEHOLDER')
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import yaml
from pydantic import BaseModel, Field, field_validator


class DataItem(BaseModel):
    """Container for a single validated configuration data point."""
    value: Any
    unit: str
    source: str
    grade: str = Field(default="A")
    status: str = Field(default="VERIFIED")

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: str) -> str:
        if not v or not str(v).strip():
            raise ValueError("Unit must not be empty. Use 'none' or 'fraction' for dimensionless values.")
        return str(v).strip()

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        if not v or not str(v).strip():
            raise ValueError("Source must not be empty.")
        return str(v).strip()

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        v_upper = str(v).strip().upper()
        if v_upper not in ("VERIFIED", "UNVERIFIED", "PLACEHOLDER", "ASSUMPTION"):
            raise ValueError(f"Status must be 'VERIFIED', 'UNVERIFIED', 'PLACEHOLDER', or 'ASSUMPTION', got '{v}'")
        return v_upper

    @field_validator("grade")
    @classmethod
    def validate_grade(cls, v: str) -> str:
        v_upper = str(v).strip().upper()
        if v_upper not in ("A", "B", "C"):
            raise ValueError(f"Grade must be 'A', 'B', or 'C', got '{v}'")
        return v_upper

    def is_placeholder(self) -> bool:
        return self.status == "PLACEHOLDER"

    def is_unverified(self) -> bool:
        return self.status == "UNVERIFIED"

    def is_assumption(self) -> bool:
        return self.status == "ASSUMPTION"


REQUIRED_CONFIG_FILES = [
    "country.yaml",
    "houses.yaml",
    "tariff.yaml",
    "capex.yaml",
    "subsidy.yaml",
    "load.yaml",
    "equipment.yaml",
]

OPTIONAL_CONFIG_FILES = [
    "lifetimes.yaml",
]


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


def validate_node(
    node: Any,
    path: str = "",
    placeholders: Optional[List[str]] = None,
    unverifieds: Optional[List[str]] = None,
    assumptions: Optional[List[str]] = None,
) -> Tuple[Any, Any]:
    """Recursively validate nodes. Returns (validated_tree_with_DataItems, stripped_values_tree)."""
    if placeholders is None:
        placeholders = []
    if unverifieds is None:
        unverifieds = []
    if assumptions is None:
        assumptions = []

    required_keys = {"value", "unit", "source", "status"}

    if isinstance(node, dict):
        if required_keys.issubset(node.keys()):
            try:
                item = DataItem(**node)
                if item.is_placeholder():
                    placeholders.append(path)
                elif item.is_unverified():
                    unverifieds.append(path)
                elif item.is_assumption():
                    assumptions.append(path)
                return item, item.value
            except Exception as e:
                raise ConfigValidationError(f"Invalid DataItem at '{path}': {e}") from e

        val_tree = {}
        strip_tree = {}
        for k, v in node.items():
            curr_path = f"{path}.{k}" if path else str(k)
            v_item, v_val = validate_node(v, curr_path, placeholders, unverifieds, assumptions)
            val_tree[k] = v_item
            strip_tree[k] = v_val
        return val_tree, strip_tree

    elif isinstance(node, list):
        val_list = []
        strip_list = []
        for i, elem in enumerate(node):
            curr_path = f"{path}[{i}]"
            e_item, e_val = validate_node(elem, curr_path, placeholders, unverifieds, assumptions)
            val_list.append(e_item)
            strip_list.append(e_val)
        return val_list, strip_list

    else:
        raise ConfigValidationError(
            f"Config value at '{path}' must be an object with {required_keys}, got primitive: {repr(node)}"
        )


class CountryConfig:
    """Loaded and validated country-specific configuration."""

    def __init__(
        self,
        country_name: str,
        raw_items: Dict[str, Any],
        values: Dict[str, Any],
        placeholders: List[str],
        unverifieds: List[str],
        assumptions: Optional[List[str]] = None,
    ):
        self.country_name = country_name
        self.raw_items = raw_items
        self.values = values
        self.placeholders = placeholders
        self.unverifieds = unverifieds
        self.assumptions = assumptions or []

    @property
    def has_placeholder(self) -> bool:
        return len(self.placeholders) > 0

    @property
    def placeholder_count(self) -> int:
        return len(self.placeholders)

    @property
    def has_unverified(self) -> bool:
        return len(self.unverifieds) > 0

    @property
    def unverified_count(self) -> int:
        return len(self.unverifieds)

    @property
    def has_assumption(self) -> bool:
        return len(self.assumptions) > 0

    @property
    def assumption_count(self) -> int:
        return len(self.assumptions)


def load_country_config(country_dir: Union[str, Path]) -> CountryConfig:
    """Loads all yaml files in country_dir/config and validates metadata strictly."""
    country_path = Path(country_dir)
    config_dir = country_path / "config"
    if not config_dir.exists():
        raise FileNotFoundError(f"Config directory not found: {config_dir}")

    all_raw_items = {}
    all_values = {}
    all_placeholders = []
    all_unverifieds = []
    all_assumptions = []

    files_to_load = list(REQUIRED_CONFIG_FILES)
    for opt_file in OPTIONAL_CONFIG_FILES:
        if (config_dir / opt_file).exists():
            files_to_load.append(opt_file)

    for file_name in files_to_load:
        file_path = config_dir / file_name
        if not file_path.exists():
            raise FileNotFoundError(f"Required config file missing: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ConfigValidationError(f"Root of {file_name} must be a dictionary")

        key_prefix = file_name.replace(".yaml", "")
        placeholders_for_file = []
        unverifieds_for_file = []
        assumptions_for_file = []
        val_tree, strip_tree = validate_node(
            data, key_prefix, placeholders_for_file, unverifieds_for_file, assumptions_for_file
        )

        all_raw_items[key_prefix] = val_tree
        all_values[key_prefix] = strip_tree
        all_placeholders.extend(placeholders_for_file)
        all_unverifieds.extend(unverifieds_for_file)
        all_assumptions.extend(assumptions_for_file)

    return CountryConfig(
        country_name=country_path.name,
        raw_items=all_raw_items,
        values=all_values,
        placeholders=all_placeholders,
        unverifieds=all_unverifieds,
        assumptions=all_assumptions,
    )
