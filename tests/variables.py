def assignment(a: bool, b: str, c: int, d: int) -> int:
    e = a
    f = b
    g = c
    h = c + d
    j = k = l = c + d + g + h
    return j + k + l if a and e or f == "hello" else 0

def annotated_assignment(a: bool, b: str, c: int, d: int) -> int:
    e: int = 3
    f: bool = a
    g: str = b
    h: int = c + d
    return e + h if a and f and g == "hello" else 0

def aug_assign(a: int, b: int) -> int:
    c = 0
    c += a
    c -= b
    c /= (a + b)
    c //= a
    c *= b
    return c

def repeated_assign(a: str, b: str) -> str:
    c = a
    c = b
    if b == a:
        c = "equal"
    return c

def pathological(a: bool, b: str, c: str) -> str:
    if a:
        d = b
    else:
        d = c
    return d
