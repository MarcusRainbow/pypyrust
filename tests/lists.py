from typing import List, Tuple

def create_list(a: int, b: int) -> List[int]:
    return [x * x for x in range(a, b)]

def process_list(a: List[int], b: List[int]) -> List[Tuple[int, int]]:
    return [(x, y) for x, y in zip(a, b)]

def add_mult_lists(a: List[float], b: List[float], c: List[float]) -> List[float]:
    d = (a + b) * c
    return d

def manual_iterator(a: List[float]) -> Tuple[float, float]:
    sum = 0.0
    prod = 1.0
    for i in a:
        sum += i
        prod *= i
    return sum, prod

def manual_dot_product(a: List[float], b: List[float]) -> float:
    sum = 0.0
    for i, j in zip(a, b):
        sum += i * j
    return sum
    
def static_lists(a: int) -> bool:
    odd = [1, 3, 5, 7]
    return a in odd

def list_methods(a: int, b: str):

    l_int = [x for x in range(a)]
    l_str = [b * x for x in range(a)]

    l_int.append(a)
    l_str.append("foo")
    l_int.insert(0, a)
    l_str.insert(2, b)
    l_int.extend([a, a + 1])
    l_str.extend([b])
    assert(l_int.sum() > 0)
    assert(l_str.count("foo") > 0)
    i = l_int.index(a)
    j = l_str.index(b)
    assert(i >= j)
    assert(l_int.min() <= l_int.max())
    l_int.reverse()
    l_str.sort()
    x_int = l_int.pop()
    x_str = l_str.pop()
    assert(x_int != a)
    assert(x_str != b)
    
    del l_int[0]
    l_str.remove(1)
