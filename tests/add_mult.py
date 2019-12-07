def add_mult(a: int, b: int, c: int) -> int:
    return a + b * c

def sub_div(a: int, b: int, c: int) -> int:
    return a - b / c

def floor_div(a: int, b: int, c: int) -> int:
    return a // (b % c)

def bitwise(a: int, b: int, c: int) -> int:
    return (a << b) & (b >> c) ^ (a | b)

def powers(a: int, b: int, c: int) -> int:
    return a * (a + b) ** ((b + c) ** (c + a))

def unaries(a: int, b: int, c: int) -> int:
    return (not (~a + +b + -c)) + ~~a

def boolean(a: bool, b: bool, c: bool) -> bool:
    return (a and b and c) or not (a or b or c)

def compare(a: int, b: int, c: int) -> bool:
    return (a == b) or (b != c) or (a > b) or (c < a) or (a <= b) or (c >= b)

def precedence(a: int, b: int, c: int) -> int:
    return a + (b - c) + (b + c) * a

def multi_compare(a: int, b: int, c: int) -> bool:
    return a < b < c or a >= b > c or a != b == c

def boolean_precedence(a: bool, b: bool, c: bool) -> bool:
    return a and b or c and b or a and c