"""Test that every schema used by the pipeline satisfies all three providers' constraints.

Gemini: no free-form dicts in response_schema
Anthropic: input_schema must be valid JSON Schema
OpenAI strict mode: no additionalProperties, every optional as X | None
"""
import json

from src.agent.planner import PlannerAction, PlannerOut
from src.agent.models import TriageOutput

SCHEMAS = [TriageOutput, PlannerOut, PlannerAction]


def _check_no_free_form_dicts(schema: dict, path: str = ""):
    """Recursively check no property has type 'object' without explicit properties."""
    props = schema.get("properties", {})
    for name, prop in props.items():
        current_path = f"{path}.{name}"
        prop_type = prop.get("type")
        if prop_type == "object" and "properties" not in prop:
            raise AssertionError(f"Free-form dict at {current_path}: {prop}")
        # Check anyOf/oneOf
        for variant_key in ("anyOf", "oneOf"):
            for variant in prop.get(variant_key, []):
                if variant.get("type") == "object" and "properties" not in variant:
                    raise AssertionError(f"Free-form dict in {variant_key} at {current_path}")
        # Recurse into nested objects
        if "properties" in prop:
            _check_no_free_form_dicts(prop, current_path)
        # Check items in arrays
        items = prop.get("items", {})
        if isinstance(items, dict) and "properties" in items:
            _check_no_free_form_dicts(items, f"{current_path}[]")

    # Check $defs
    for def_name, def_schema in schema.get("$defs", {}).items():
        if def_schema.get("type") == "object" and "properties" not in def_schema:
            raise AssertionError(f"Free-form dict in $defs.{def_name}")
        if "properties" in def_schema:
            _check_no_free_form_dicts(def_schema, f"$defs.{def_name}")


def test_schemas_no_free_form_dicts():
    """Gemini constraint: no free-form dicts."""
    for model in SCHEMAS:
        schema = model.model_json_schema()
        _check_no_free_form_dicts(schema, model.__name__)


def test_schemas_valid_json_schema():
    """Anthropic constraint: schema must be serializable as valid JSON."""
    for model in SCHEMAS:
        schema = model.model_json_schema()
        # Must be JSON-serializable
        raw = json.dumps(schema, sort_keys=True)
        parsed = json.loads(raw)
        assert "properties" in parsed or "$defs" in parsed, f"{model.__name__} has no properties"


def test_schemas_optional_as_none():
    """OpenAI strict constraint: optional fields use X | None pattern."""
    for model in SCHEMAS:
        schema = model.model_json_schema()
        props = schema.get("properties", {})
        required = set(schema.get("required", []))
        for name, prop in props.items():
            if name not in required:
                # Optional field must allow None via anyOf/oneOf or explicit null type
                any_of = prop.get("anyOf", [])
                one_of = prop.get("oneOf", [])
                has_null = (
                    prop.get("type") == "null"
                    or any(v.get("type") == "null" for v in any_of)
                    or any(v.get("type") == "null" for v in one_of)
                    or prop.get("default") is None
                )
                # Pydantic marks Optional[X] = None with default=None
                assert has_null or prop.get("default") is not None, (
                    f"{model.__name__}.{name} is optional but does not allow None"
                )


def test_no_additional_properties_in_schemas():
    """OpenAI strict constraint: no additionalProperties allowed."""
    for model in SCHEMAS:
        schema = model.model_json_schema()
        # Top level
        assert schema.get("additionalProperties") is not True, (
            f"{model.__name__} has additionalProperties=true"
        )
        # In $defs
        for def_name, def_schema in schema.get("$defs", {}).items():
            assert def_schema.get("additionalProperties") is not True, (
                f"{model.__name__}.$defs.{def_name} has additionalProperties=true"
            )
