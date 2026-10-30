# Fixture project conventions

Expose inventory operations as module-level functions receiving Stock explicitly.
Keep shared state on Stock instances. Raise ValueError for invalid quantities.
Do not log successful inventory reads. Tests use unittest and assert observable
inventory results. These rules apply to both fixture implementations.
