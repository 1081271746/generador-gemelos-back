"""Sampling grammar is not the final validator. Never fill or drop output fields."""
EXPENSIVE_GRAMMAR_BOUNDS = {"minLength", "maxLength", "minItems", "maxItems"}
NAMED_SCHEMAS = {"properties", "$defs", "definitions", "patternProperties"}


def structural_schema(value):
    """Preserve shape/required/enums/numeric bounds, defer lengths to Pydantic."""
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key in EXPENSIVE_GRAMMAR_BOUNDS:
                continue
            if key in NAMED_SCHEMAS and isinstance(item, dict):
                result[key] = {name: structural_schema(child) for name, child in item.items()}
            else:
                result[key] = structural_schema(item)
        return result
    if isinstance(value, list):
        return [structural_schema(item) for item in value]
    return value
