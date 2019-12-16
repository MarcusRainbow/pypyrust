from typing import Tuple

def use_tuple_for_swap(a: int, b: int) -> int:
    if b > a:
        a, b = b, a
    return a - b

def return_tuple(a: int, b: int) -> Tuple[int, int]:
    return (a, b)

def use_returned_tuple(a: int, b: int) -> int:
    c, d = return_tuple(a, b)
    return use_tuple_for_swap(c, d)

def tuple_in_args(a: Tuple[int, int]) -> int:
    if a[1] > a[0]:
        a = a[1], a[0]
    return a[0] - a[1]
