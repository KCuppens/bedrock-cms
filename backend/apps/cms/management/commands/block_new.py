from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.template import Context, Template

import pytest
from rest_framework.exceptions import ValidationError

from apps.cms.blocks.validation import validate_blocks, {{ block_class }}BlockModel

Management command to scaffold new block types.

class Command(BaseCommand):
    help = "Create a new block type with schema, tests, and documentation"

    def add_arguments(self, parser):
        parser.add_argument(
            "block_type",
            type=str,
            help='Block type name (e.g., "testimonial", "pricing_table")',
        )
        parser.add_argument(
            "--description", type=str, default="", help="Description of the block"
        )
        parser.add_argument(
            "--props",
            nargs="*",
            default=[],
            help='Block properties in format "prop_name:type:default" (e.g., "title:str:Welcome" "count:int:3")',
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without actually creating files",
        )

    def handle(self, *args, **options):
        block_type = options["block_type"]
        description = options["description"]
        props = options["props"]
        dry_run = options["dry_run"]

        # Validate block type name
        if not block_type.replace("_", "").isalnum():
            raise CommandError(
                "Block type name must contain only letters, numbers, and underscores"
            )

        # Parse properties
        parsed_props = self._parse_properties(props)

        # Generate context for templates
        context = {
            "block_type": block_type,
            "block_class": self._to_pascal_case(block_type),
            "block_title": self._to_title_case(block_type),
            "description": description or f"{self._to_title_case(block_type)} block",
            "props": parsed_props,
        }

        self.stdout.write(self.style.SUCCESS(f"Creating new block type: {block_type}"))

        if dry_run:
            self._show_dry_run(context)

        try:
            # Update validation.py
            self._update_validation_file(context)

            # Create test file
            self._create_test_file(context)

            # Create documentation
            self._create_docs_file(context)

            self.stdout.write(
                self.style.SUCCESS(f"Successfully created block type: {block_type}")
            )
            self._show_next_steps(context)

        except Exception as e:
            raise CommandError(f"Failed to create block: {e}")

    def _parse_properties(self, props):
        """Parse property definitions into structured format."""
        parsed = []

        for prop in props:
            parts = prop.split(":", 2)
            if len(parts) < 2:
                raise CommandError(
                    f'Invalid property format: {prop}. Use "name:type:default"'
                )

            name = parts[0]
            prop_type = parts[1]
            default = parts[2] if len(parts) > 2 else ""

            # Map types to Python/Pydantic types
            type_mapping = {
                "str": "str",
                "string": "str",
                "int": "int",
                "integer": "int",
                "float": "float",
                "bool": "bool",
                "boolean": "bool",
                "list": "List[str]",
                "dict": "Dict[str, Any]",
                "url": "HttpUrl",
            }

            python_type = type_mapping.get(prop_type, "str")

            # Generate appropriate default values
            if not default:
                if prop_type in ["str", "string"]:
                    default = '""'
                elif prop_type in ["int", "integer"]:
                    default = "0"
                elif prop_type in ["float"]:
                    default = "0.0"
                elif prop_type in ["bool", "boolean"]:
                    default = "False"
                elif prop_type in ["list"]:
                    default = "[]"
                elif prop_type in ["dict"]:
                    default = "{}"
                else:
                    default = '""'
            elif prop_type in ["str", "string"]:
                default = f'"{default}"'

            parsed.append(
                {
                    "name": name,
                    "type": python_type,
                    "default": default,
                    "description": f"{name.replace('_', ' ').title()} field",
                }
            )

        return parsed

    def _to_pascal_case(self, text):
        """Convert snake_case to PascalCase."""
        return "".join(word.capitalize() for word in text.split("_"))

    def _to_title_case(self, text):
        """Convert snake_case to Title Case."""
        return " ".join(word.capitalize() for word in text.split("_"))

    def _show_dry_run(self, context):
        """Show what would be created in dry run mode."""
        self.stdout.write("\nFiles that would be created/modified:")
        self.stdout.write("  * apps/cms/blocks/validation.py (updated)")
        self.stdout.write(
            f"  * tests/unit/test_blocks_{context['block_type']}.py (new)"
        )
        self.stdout.write(f"  * docs/blocks/{context['block_type']}.md (new)")

        self.stdout.write("\nBlock schema preview:")
        schema_content = self._generate_block_schema(context)
        self.stdout.write(schema_content)

    def _update_validation_file(self, context):
        """Add new block model to validation.py."""
        validation_file = Path("apps/cms/blocks/validation.py")

        if not validation_file.exists():
            raise CommandError("validation.py file not found")

        # Read current content
        with open(validation_file) as f:
            content = f.read()

        # Generate new block model
        block_model = self._generate_block_schema(context)

        # Find insertion point (before BLOCK_MODELS registry)
        registry_line = "BLOCK_MODELS: Dict[str, type[BaseBlockModel]] = {"
        if registry_line not in content:
            raise CommandError("Could not find BLOCK_MODELS registry in validation.py")

        # Insert new block model before registry
        parts = content.split(registry_line)
        new_content = (
            parts[0]
            + block_model
            + "\n\n# Registry of all block models\n"
            + registry_line
            + parts[1]
        )

        # Add to registry
        registry_entry = (
            f'    "{context["block_type"]}": {context["block_class"]}BlockModel,'
        )
        registry_end = "}"

        # Find the registry closing brace and insert before it
        registry_parts = new_content.split(registry_end)
        if len(registry_parts) < 2:
            raise CommandError("Could not find end of BLOCK_MODELS registry")

        new_content = (
            registry_parts[0]
            + registry_entry
            + "\n"
            + registry_end
            + registry_end.join(registry_parts[1:])
        )

        # Write back to file
        with open(validation_file, "w") as f:
            f.write(new_content)

        self.stdout.write("  * Updated apps/cms/blocks/validation.py")

    def _generate_block_schema(self, context):
        """Generate Pydantic block model."""
        template = Template(
            '''
class {{ block_class }}BlockModel(BaseBlockModel):
    """{{ description }}."""
    type: Literal["{{ block_type }}"]
    props: Dict[str, Any] = Field(default_factory=lambda: {
        {% for prop in props %}"{{ prop.name }}": {{ prop.default }},{% if not forloop.last %}
        {% endif %}{% endfor %}
    })
'''
        )

        return template.render(Context(context))

    def _create_test_file(self, context):
        """Create test file for the new block."""
        test_dir = Path("tests/unit")
        test_dir.mkdir(parents=True, exist_ok=True)

        test_file = test_dir / f"test_blocks_{context['block_type']}.py"

        template = Template(
            '''"""
Tests for {{ block_type }} block.

class Test{{ block_class }}Block:
    """Tests for {{ block_type }} block validation."""

    def test_valid_{{ block_type }}_block(self):
        """Test valid {{ block_type }} block validates successfully."""
        blocks = [{
            "type": "{{ block_type }}",
            "schema_version": 1,
            "props": {
                {% for prop in props %}"{{ prop.name }}": {{ prop.default }},{% if not forloop.last %}
                {% endif %}{% endfor %}
            }
        }]

        validated = validate_blocks(blocks)
        assert len(validated) == 1
        assert validated[0]["type"] == "{{ block_type }}"
        assert validated[0]["schema_version"] == 1

    def test_{{ block_type }}_block_defaults(self):
        """Test {{ block_type }} block applies default values."""
        blocks = [{
            "type": "{{ block_type }}"
        }]

        validated = validate_blocks(blocks)
        block = validated[0]

        assert block["schema_version"] == 1
        assert "props" in block
        {% for prop in props %}assert "{{ prop.name }}" in block["props"]
        {% endfor %}

    def test_{{ block_type }}_block_pydantic_model(self):
        """Test {{ block_type }} block Pydantic model directly."""
        data = {
            "type": "{{ block_type }}",
            "schema_version": 1,
            "props": {
                {% for prop in props %}"{{ prop.name }}": {{ prop.default }},{% if not forloop.last %}
                {% endif %}{% endfor %}
            }
        }

        model = {{ block_class }}BlockModel(**data)
        assert model.type == "{{ block_type }}"
        assert model.schema_version == 1
        {% for prop in props %}assert model.props["{{ prop.name }}"] == {{ prop.default }}
        {% endfor %}

    def test_invalid_{{ block_type }}_block_type(self):
        """Test invalid block type is rejected."""
        blocks = [{
            "type": "wrong_type",
            "props": {}
        }]

        with pytest.raises(ValidationError) as exc_info:
            validate_blocks(blocks)

        errors = exc_info.value.detail["errors"]
        assert any("Unknown block type" in error["msg"] for error in errors)

    {% if props %}def test_{{ block_type }}_block_type_validation(self):
        """Test property type validation."""
        # This test should be customized based on your specific property types
        blocks = [{
            "type": "{{ block_type }}",
            "props": {
                # Add test cases for invalid property values here
                {% for prop in props %}# "{{ prop.name }}": # invalid_value,
                {% endfor %}
            }
        }]

        # Uncomment and customize based on your validation needs
        # with pytest.raises(ValidationError):
        #     validate_blocks(blocks)
    {% endif %}
'''
        )

        with open(test_file, "w") as f:
            f.write(template.render(Context(context)))

        self.stdout.write(f"  * Created {test_file}")

    def _create_docs_file(self, context):
        """Create documentation file for the new block."""
        docs_dir = Path("docs/blocks")
        docs_dir.mkdir(parents=True, exist_ok=True)

        docs_file = docs_dir / f"{context['block_type']}.md"

        template = Template(
            """# {{ block_title }} Block

{{ description }}

## Schema

```json
{
  "type": "{{ block_type }}",
  "schema_version": 1,
  "props": {
    {% for prop in props %}"{{ prop.name }}": {{ prop.default }}{% if not forloop.last %},{% endif %}
    {% endfor %}
  }
}
```

## Properties

{% for prop in props %}### `{{ prop.name }}` ({{ prop.type }})

{{ prop.description }}

- **Default**: `{{ prop.default }}`
- **Required**: No

{% endfor %}

## Usage Examples

### Basic Example

```json
{
  "type": "{{ block_type }}",
  "props": {
    {% for prop in props %}"{{ prop.name }}": {{ prop.default }}{% if not forloop.last %},{% endif %}
    {% endfor %}
  }
}
```

{% if props %}### Customized Example

```json
{
  "type": "{{ block_type }}",
  "props": {
    {% for prop in props %}"{{ prop.name }}": {{ prop.default }} // Customize this value{% if not forloop.last %},{% endif %}
    {% endfor %}
  }
}
```
{% endif %}

## Frontend Implementation

To render this block in your frontend, handle the `{{ block_type }}` type in your block renderer:

```javascript
// React example
function {{ block_class }}Block({ props }) {
  const { {% for prop in props %}{{ prop.name }}{% if not forloop.last %}, {% endif %}{% endfor %} } = props;

  return (
    <div className="{{ block_type }}-block">
      {/* Implement your {{ block_type }} rendering logic here */}
      {% for prop in props %}{% if prop.type == "str" %}<span>{​{ {{ prop.name }} }​}</span>
      {% endif %}{% endfor %}
    </div>
  );
}
```

## Validation

This block is validated using the `{{ block_class }}BlockModel` Pydantic model. The following validations are applied:

- Block type must be exactly `"{{ block_type }}"`
- Schema version defaults to `1`
{% for prop in props %}- `{{ prop.name }}` must be of type `{{ prop.type }}`
{% endfor %}

## Testing

Run the tests for this block:

```bash
pytest tests/unit/test_blocks_{{ block_type }}.py -v
```

## See Also

- [Block System Overview](../blocks.md)
- [Block Validation](../validation.md)
- [Creating Custom Blocks](../custom-blocks.md)

        )

        with open(docs_file, "w") as f:
            f.write(template.render(Context(context)))

        self.stdout.write(f"  * Created {docs_file}")

    def _show_next_steps(self, context):
        """Show next steps to the user."""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("NEXT STEPS")
        self.stdout.write("=" * 50)

        self.stdout.write("\n1. Review the generated files:")
        self.stdout.write("   - Check the block schema in validation.py")
        self.stdout.write(
            f"   - Review tests in tests/unit/test_blocks_{context['block_type']}.py"
        )
        self.stdout.write(
            f"   - Update documentation in docs/blocks/{context['block_type']}.md"
        )

        self.stdout.write("\n2. Run the tests:")
        self.stdout.write(
            f"   python manage.py test tests.unit.test_blocks_{context['block_type']}"
        )

        self.stdout.write("\n3. Test the block validation:")
        self.stdout.write("   python manage.py shell")
        self.stdout.write(
            "   >>> from apps.cms.blocks.validation import validate_blocks"
        )
        self.stdout.write(
            f'   >>> blocks = [{{"type": "{context["block_type"]}", "props": {{}}}}]'
        )
        self.stdout.write("   >>> validate_blocks(blocks)")

        self.stdout.write("\n4. Implement frontend rendering for the block")

        self.stdout.write(
            "\n5. Add the block to your page templates or admin interface"
        )

        self.stdout.write(f'\nBlock "{context["block_type"]}" is ready to use!')
