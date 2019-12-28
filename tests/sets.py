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

def set_methods(a: int, b: str):

    s_int = {x for x in range(a)}
    s_str = {b * x for x in range(a)}

    s_int.add(a)
    s_str.add("foo")

    copy_s_int = s_int.copy()
    assert(copy_s_int == s_int)
    assert(copy_s_int is not s_int)

    diff_s_int = s_int.difference(copy_s_int)
    assert(len(diff_s_int) == 0)
    copy_s_int.clear()
    assert(copy_s_int != s_int)

    diff_s_int.difference_update(s_int)
    assert(diff_s_int == s_int)

    s_int.discard(0)
    s_str.discard("baz")

    union_s_int = s_int.union(copy_s_int)
    assert(copy_s_int == union_s_int)
    inter_s_int = s_int.intersection(copy_s_int)
    s_int.intersection_update(copy_s_int, inter_s_int)
    assert(s_int != inter_s_int)
    assert(not s_int.isdisjoint(inter_s_int))

    assert(inter_s_int.issubset(s_int))
    assert(s_int.issuperset(inter_s_int))

    sd_s_int = s_int.symmetric_difference(copy_s_int)
    s_int.symmetric_difference_update(copy_s_int, sd_s_int)
    
    del s_int[0]
    s_int.remove(1)
    s_str.remove("foo")
