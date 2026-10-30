# Specification fixture, revision fixture-1

U-01: see request.md. This is a review fixture, not an implementation plan.

reserve(stock, sku, quantity) accepts a positive integer quantity. It returns True
and decrements stock when enough units are available; otherwise it returns False
without modifying stock. Nonpositive quantities raise ValueError without changes.
Concurrent reservations on the same Stock instance must never oversell inventory.
The existing available(stock, sku) API remains callable and returns current stock.

Developer journey: create a Stock with one unit, call reserve twice for one unit;
observe True then False, and available returns zero. Concurrent attempts have the
same invariant: only one succeeds. Invalid input visibly raises ValueError.
