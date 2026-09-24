Promise type for editing values inside `yaml` files.

Edits are applied as small text splices on the original lines, so comments, key order, quoting style and formatting of everything not touched by the promise are preserved.

## Promiser

Path to the YAML file to edit. It must have a `.yaml` or `.yml` extension.

A missing file is treated as an empty document: `set` and `present` create it (with mode 0600), `absent` leaves it missing.
The directory must already exist.

## Attributes

| Name        | Type     | Required                     | Description                                        |
| ----------- | -------- | ---------------------------- | -------------------------------------------------- |
| `filter`    | `string` | yes                          | jq-like path to the node(s) to operate on          |
| `operation` | `string` | yes                          | One of `set`, `present` or `absent`                |
| `value`     | `string` | for `set` and `present`      | A scalar value                                     |

### Operations

All operations describe a desired state, so running a promise again once it is kept changes nothing.

- `set`: The key or item has `value`. Creates the key if it's missing, along with any missing parent keys, or replaces the current value, including nested content.
  The quoting style of an existing value (plain, single or double quoted) is kept.
- `present`: The sequence at `filter` contains `value`. Appends it if it's missing, creating the sequence (and parent keys) if needed.
- `absent`: Without `value`, the key(s) or item(s) at `filter` don't exist.
  With `value`, the sequence at `filter` doesn't contain `value`.

Sequence items are matched by content, not by position: use `value`, or `select()` for sequences of mappings.
`absent` on a plain index like `.hosts[1]` is rejected, since the next run would remove whatever moved into that position.

`true`, `false`, `null` and numbers are written as-is, so `value => "false"` writes a boolean.
Values that would be misread (e.g. `no`, `on`, `22:22`, or anything containing `: `) are quoted.

### Filter syntax

| Syntax                         | Meaning                                                   |
| ------------------------------ | --------------------------------------------------------- |
| `.a.b.c`                       | Key access                                                |
| `.a["b.c"]`                    | Quoted key access (keys with dots, spaces, etc.)          |
| `.a[1]`, `.a[-1]`              | Sequence index (negative counts from the end)             |
| `.a[]`                         | Every item of a sequence                                  |
| `.a[] \| select(.b == "x")`    | Items where `.b` equals a string, number, `true`, `false` or `null` |
| `... \| .c`                    | Continue from each selected item                          |

A filter can match several nodes (e.g. `.hosts[].port`); the operation is applied to all of them.
A `select()` that matches nothing is kept.
Missing parents are only created for plain key paths like `.a.b.c`, not through `[]`, indexes or `select()`.

## Example

Given a Kubernetes deployment `/srv/k8s/shop.yaml`:

```yaml
spec:
  replicas: 2
  template:
    spec:
      containers:
        - name: app
          image: "registry.example.com/shop:1.4.0" # bumped by CI
          args:
            - --port=8080
        - name: log-shipper
          image: fluent/fluent-bit:2.1
```

the policy

```cfengine3
bundle agent main
{
  yaml:
    "/srv/k8s/shop.yaml"
      filter => ".spec.replicas",
      operation => "set",
      value => "3";

    "/srv/k8s/shop.yaml"
      filter => '.spec.template.spec.containers[] | select(.name == "app") | .image',
      operation => "set",
      value => "registry.example.com/shop:1.5.0";

    "/srv/k8s/shop.yaml"
      filter => '.spec.template.spec.containers[] | select(.name == "app") | .args',
      operation => "present",
      value => "--metrics";

    "/srv/k8s/shop.yaml"
      filter => '.spec.template.spec.containers[] | select(.name == "log-shipper")',
      operation => "absent";
}
```

results in:

```yaml
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: app
          image: "registry.example.com/shop:1.5.0" # bumped by CI
          args:
            - --port=8080
            - --metrics
```

## Limitations

This module ships its own minimal YAML parser (`yaml_lite.py`) and does not depend on PyYAML.
It only understands a subset of YAML:

- Block mappings, block sequences, plain/quoted scalars and comments are supported
- Block scalars (`|` / `>`), flow collections (`{...}` / `[...]`), anchors, aliases and tags are not supported
- Only scalar values can be written; nested structures can not be created with `value`

## Tests

`tests/*.cf` are self-contained policies. With the module installed, run them as root with `cf-agent -KIf <file>.cf`; each prints `Pass` or `FAIL`.

## Authors

This software was created by the team at [Northern.tech](https://northern.tech), with many contributions from the community.
Thanks everyone!

## Contribute

Feel free to open pull requests to expand this documentation, add features, or fix problems.
You can also pick up an existing task or file an issue in [our bug tracker](https://northerntech.atlassian.net/).

## License

This software is licensed under the MIT License. See LICENSE in the root of the repository for the full license text.
