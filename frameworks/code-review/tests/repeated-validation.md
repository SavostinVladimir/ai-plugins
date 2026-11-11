# Repeated validation across calls

Send this file only to code-simplicity as a separate proposed module. Treat all
definitions below as the complete reachable implementation for this scenario.

```python
def read_value(source):
    value = source.read()
    if value == "":
        raise ValueError("empty value")
    return value


def use_value(source):
    value = read_value(source)
    if value == "":
        raise ValueError("empty value")
    return value


def use_nonblank_value(source):
    value = read_value(source)
    if value.strip() == "":
        raise ValueError("blank value")
    return value
```
