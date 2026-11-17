"""Optional schema parity tests use an already installed validator, never runtime."""

import unittest

from stemlab.validation import read_json
from test_configuration import ROOT, example, invalid_examples

try:
    from jsonschema import Draft202012Validator, ValidationError
    from referencing import Registry, Resource
except ImportError:
    Draft202012Validator = None


@unittest.skipIf(Draft202012Validator is None, "optional jsonschema test tool is not installed")
class SchemaTests(unittest.TestCase):
    def setUp(self):
        schemas = [read_json(path) for path in sorted((ROOT / "src/stemlab/schemas").glob("*.json"))]
        self.registry = Registry().with_resources((schema["$id"], Resource.from_contents(schema)) for schema in schemas)
        self.schemas = {schema["$id"].rsplit("/", 1)[1]: schema for schema in schemas}

    def validator(self, name):
        return Draft202012Validator(self.schemas[name], registry=self.registry)

    def test_schemas_are_valid(self):
        for schema in self.schemas.values():
            Draft202012Validator.check_schema(schema)

    def test_examples_conform_without_network_resolution(self):
        self.validator("experiment.schema.json").validate(example())
        for path in (ROOT / "examples/environments").glob("*.json"):
            with self.subTest(path=path):
                self.validator("environment.schema.json").validate(read_json(path))

    def test_runtime_and_schema_reject_same_invalid_examples(self):
        for name, data in invalid_examples():
            with self.subTest(name=name), self.assertRaises(ValidationError):
                self.validator("experiment.schema.json").validate(data)
