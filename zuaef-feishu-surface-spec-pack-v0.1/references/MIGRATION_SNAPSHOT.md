# Reference Snapshot — Migration from lark_oapi.channel

Current architecture direction:

Old Channel import:
```python
# legacy channel location
# from lark_oapi.channel import FeishuChannel
```

Current standalone package:
```python
from lark_channel import FeishuChannel
```

Install:
```text
lark-channel-sdk
```

The standalone Channel SDK can coexist with `lark-oapi`.

Use:
- `lark-channel-sdk` for conversational Channel bot workflows;
- `lark-oapi` only if a separate feature needs the broad OpenAPI SDK.

Do not migrate unrelated OpenAPI code merely as part of this task.
