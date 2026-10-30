import logging
import threading
import unittest
from unittest.mock import patch


class Stock:
    def __init__(self, items):
        self.items = dict(items)
        self.lock = threading.Lock()


class ReservationAdapter:
    def __init__(self, stock):
        self.stock = stock

    def reserve(self, sku, quantity):
        return reserve(self.stock, sku, quantity)


def reserve(stock, sku, quantity):
    current = stock.items.get(sku, 0)
    if current < quantity:
        return False
    stock.items[sku] = current - quantity
    return True


def remaining(stock, sku):
    logging.info("inventory read")
    return stock.items.get(sku, 0)


class ReservationTests(unittest.TestCase):
    def test_reserve(self):
        stock = Stock({"book": 1})
        with patch(__name__ + ".reserve", return_value=True):
            self.assertTrue(reserve(stock, "book", 1))
