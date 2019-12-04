def if_else(a: bool, c: int) -> int:
    if a:
        return c
    else:
        return 42

def return_if_else(a: bool, c: int) -> int:
    return c if a else 42

def if_elif_else(a: bool, b: bool, c: str, d:str) -> str:
    if a and b:
        return c
    elif a or b:
        return d
    else:
        return "Neither"

def while_loop(a: bool, b: bool):
    # the code doesn't have to be sensible
    while a or b:
        print("hello")

def while_break_continue(a: bool, b: bool):
    while True:
        if a:
            break
        elif b:
            continue
        print("hello")
