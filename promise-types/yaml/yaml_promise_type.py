import os

from cfengine_module_library import PromiseModule, ValidationError, Result

import yaml_lite
import jq_filter

_OPERATIONS = ("set", "present", "absent")

# Each repair changes one match and re-parses the file, so this only guards
# against an operation that never converges
_MAX_REPAIRS = 1000


class YamlPromiseTypeModule(PromiseModule):
    def __init__(self):
        super(YamlPromiseTypeModule, self).__init__("yaml_promise_module", "0.0.0")

    def validate_promise(self, promiser, attributes, metadata):
        if not promiser.endswith((".yaml", ".yml")):
            raise ValidationError(
                "'%s' is not recognized as a yaml file (expected .yaml/.yml extension)"
                % promiser
            )

        filter_text = attributes.get("filter")
        if not filter_text:
            raise ValidationError("Attribute 'filter' is required")
        try:
            steps = jq_filter.parse_filter(filter_text)
        except jq_filter.FilterError as e:
            raise ValidationError("Invalid 'filter': %s" % e)

        operation = attributes.get("operation")
        if operation not in _OPERATIONS:
            raise ValidationError(
                "Attribute 'operation' must be one of: %s" % ", ".join(_OPERATIONS)
            )

        if operation in ("set", "present") and "value" not in attributes:
            raise ValidationError(
                "Attribute 'value' is required for operation '%s'" % operation
            )

        # Removing by position is not convergent: the next run would remove
        # whatever moved into that position
        if (
            operation == "absent"
            and "value" not in attributes
            and isinstance(steps[-1], jq_filter.IndexStep)
        ):
            raise ValidationError(
                "Operation 'absent' can not remove a sequence item by index, "
                "use 'value' or select() to match it by content"
            )

    def evaluate_promise(self, promiser, attributes, metadata):
        operation = attributes["operation"]
        filter_text = attributes["filter"]
        value = attributes.get("value")
        steps = jq_filter.parse_filter(filter_text)

        if not os.path.isfile(promiser):
            content = ""
        else:
            with open(promiser, "r") as f:
                content = f.read()

        changed = False
        for _ in range(_MAX_REPAIRS):
            lines, root = yaml_lite.parse_document(content)
            if root is None:
                self.log_error(
                    "'%s' has no YAML content to operate on "
                    "(use a files: promise to create it first)" % promiser
                )
                return Result.NOT_KEPT
            try:
                matches = jq_filter.evaluate(steps, root)
                if not _repair_one(lines, matches, operation, value):
                    break
            except (jq_filter.FilterError, _OperationError) as e:
                self.log_error(
                    "Filter '%s' failed on '%s': %s" % (filter_text, promiser, e)
                )
                return Result.NOT_KEPT
            content = "".join(lines)
            changed = True
        else:
            self.log_error(
                "'%s' did not converge for filter '%s'" % (promiser, filter_text)
            )
            return Result.NOT_KEPT

        if not changed:
            return Result.KEPT

        with open(promiser, "w") as f:
            f.write(content)
        self.log_info(
            "Updated '%s' (filter '%s', operation '%s')"
            % (promiser, filter_text, operation)
        )
        return Result.REPAIRED


class _OperationError(Exception):
    pass


def _repair_one(lines, matches, operation, value):
    """Fix the first match that isn't in the desired state. Returns False if
    all matches are already in the desired state."""
    for match in matches:
        if operation == "set":
            if _set(lines, match, value):
                return True
        elif operation == "present":
            if _present(lines, match, value):
                return True
        elif value is not None:
            if _absent_item(lines, match, value):
                return True
        elif match.exists:
            yaml_lite.delete_slot(lines, yaml_lite.get_slot(match.container, match.key))
            return True
    return False


def _set(lines, match, value):
    if not match.exists:
        if isinstance(match.container, yaml_lite.SequenceNode):
            raise _OperationError("Can not set a sequence item that does not exist")
        yaml_lite.insert_mapping_key(
            lines, match.container, match.key, yaml_lite.format_scalar(value)
        )
        return True
    node = match.node
    style = node.style if isinstance(node, yaml_lite.ScalarNode) else None
    new_text = yaml_lite.format_scalar(value, style)
    if isinstance(node, yaml_lite.ScalarNode) and node.raw == new_text:
        return False
    yaml_lite.set_slot_value(
        lines, yaml_lite.get_slot(match.container, match.key), new_text
    )
    return True


def _sequence_or_slot(match):
    """The sequence the filter points at, or the empty 'key:' slot to create
    it under."""
    if isinstance(match.node, yaml_lite.SequenceNode):
        return match.node
    if match.exists and match.node is None:
        return yaml_lite.get_slot(match.container, match.key)
    raise _OperationError("'value' with 'present'/'absent' requires a sequence")


def _item_text(node):
    if not isinstance(node, yaml_lite.ScalarNode):
        return None
    return node.raw if node.style == "plain" else node.value


def _present(lines, match, value):
    seq = _sequence_or_slot(match)
    if isinstance(seq, yaml_lite.SequenceNode):
        if any(_item_text(item.value) == value for item in seq.items):
            return False
    yaml_lite.append_sequence_item(lines, seq, yaml_lite.format_scalar(value))
    return True


def _absent_item(lines, match, value):
    seq = _sequence_or_slot(match)
    if not isinstance(seq, yaml_lite.SequenceNode):
        return False
    for item in seq.items:
        if _item_text(item.value) == value:
            yaml_lite.delete_slot(lines, item)
            return True
    return False


if __name__ == "__main__":
    YamlPromiseTypeModule().start()
