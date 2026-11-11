# Layout preservation

Send this scenario only to code-style, together with the fixture README. Review
each after snippet against its before snippet. No project rule or formatter
requires a layout change in these cases.

## Inline expression

Before:

```python
result = build(first, second)
```

After A:

```python
result = build(first, second, third)
```

After B:

```python
result = build(
    first,
    second,
    third,
)
```

## One entry per line

Before:

```python
result = build(
    first,
    second,
)
```

After A:

```python
result = build(
    first,
    second,
    third,
)
```

After B:

```python
result = build(
    first, second,
    third,
)
```
