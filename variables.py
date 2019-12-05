def assignment(a: bool, b: str, c: int, d: int):
    e = a
    f = b
    g = c
    h = c + d
    j = k = l = c + d + g + h

def annotated_assignment(a: bool, b: str, c: int, d: int):
    e: int = 3
    f: bool = a
    g: str = c
    h: int = c + d

def aug_assign(a: int, b: int):
    c = 0
    c += a
    c -= b
    c /= (a + b)
    c //= a
    c *= b
    