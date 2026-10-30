import threading
import unittest


class Stock:
    def __init__(self, items):
        self.items = dict(items)
        self.lock = threading.Lock()


def reserve(stock, sku, quantity):
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    with stock.lock:
        current = stock.items.get(sku, 0)
        if current < quantity:
            return False
        stock.items[sku] = current - quantity
        return True


def available(stock, sku):
    with stock.lock:
        return stock.items.get(sku, 0)


class ReservationTests(unittest.TestCase):
    def test_reserve_and_exhaust(self):
        stock = Stock({"book": 1})
        self.assertTrue(reserve(stock, "book", 1))
        self.assertEqual(available(stock, "book"), 0)
        self.assertFalse(reserve(stock, "book", 1))
        self.assertEqual(available(stock, "book"), 0)

    def test_invalid_quantity_keeps_stock(self):
        stock = Stock({"book": 1})
        for quantity in (0, -1):
            with self.assertRaises(ValueError):
                reserve(stock, "book", quantity)
            self.assertEqual(available(stock, "book"), 1)

    def test_concurrent_reservations(self):
        stock = Stock({"book": 1})
        start = threading.Barrier(2)

        def attempt():
            start.wait(timeout=5)
            return reserve(stock, "book", 1)

        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(attempt) for _ in range(2)]
            results = [future.result(timeout=10) for future in futures]
        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(available(stock, "book"), 0)
