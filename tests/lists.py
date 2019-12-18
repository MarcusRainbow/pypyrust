from typing import List, Tuple

def create_list(a: int, b: int) -> List[int]:
    return [x * x for x in range(a, b)]

def process_list(a: List[int], b: List[int]) -> List[int]:
    return [(x, y) for x, y in zip(a, b)]

def add_mult_lists(a: List[float], b: List[float], c: List[float]) -> List[float]:
    d = (a + b) * c
    return d

def manual_iterator(a: List[float]) -> Tuple[float, float]:
    sum = 0.0
    prod = 1.0
    for i in a:
        sum += a[i]
        prod *= a[i]
    return sum, prod

def manual_dot_product(a: List[float], b: List[float]) -> float:
    sum = 0
    for i, j in zip(a, b):
        sum += i * j
    return sum
    