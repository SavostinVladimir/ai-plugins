# Синтетическая переписка

Проект: `/workspace/catalog-api`. Задача: вернуть количество доступных товаров.
Сессия: `journal-example`, сообщения имеют указанные ниже ID.

## A1 — агент написал код

`stock.py`:

```python
class AvailabilityAdapter:
    def __init__(self, stock):
        self.stock = stock

    def available(self, sku):
        return self.stock.available(sku)


def available(stock, sku):
    return AvailabilityAdapter(stock).available(sku)
```

## U1 — пользователь

«Убери AvailabilityAdapter: он только пересылает вызов. Вызывай stock.available напрямую».

## A2 — агент исправил

```python
def available(stock, sku):
    return stock.available(sku)
```

Проверка: `python3 -m unittest` — 3 теста прошли.

## U2 — пользователь

«Теперь переименуй sku в product_id. У нас внешний контракт использует product_id».

## A3 — агент исправил

```python
def available(stock, product_id):
    return stock.available(product_id)
```

Проверка: `python3 -m unittest` — 3 теста прошли.
Явного принятия пользователем в доступной истории нет.

## U3 — пользователь

«Теперь переименуй sku в product_id. У нас внешний контракт использует product_id».

## A4 — агент ответил

The available function already uses product_id. No further code changes were needed.
I did not rerun the tests.
