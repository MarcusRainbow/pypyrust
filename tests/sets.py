from typing import Set

def create_set(a: int, b: int) -> Set[int]:
    return {i for i in range(a, b)}

def set_check_and_add(a: Set[str], item: str) -> bool:
    if item in a:
        return True
    else:
        a.add(item)
        return False

def create_static_set() -> Set[str]:
    a = { "one", "two", "three" }
    return a

