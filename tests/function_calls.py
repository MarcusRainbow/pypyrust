import flow_of_control
import add_mult

def call_add_mult(a: int, b: int, c: int) -> int:
    d = add_mult.add_mult(a, b, c)
    e = add_mult.sub_div(a, b, c)
    return d + e

def call_flow_of_control(a: bool, b: int) -> int:
    c = flow_of_control.if_else(a, b)
    d = flow_of_control.return_if_else(a, b)
    e = flow_of_control.if_elif_else(a, not a, "hello", "world")
    flow_of_control.while_loop(a, not a)
    return c if e == "Foo" else d

def call_local(a: int, b: int, c: int) -> int:
    if a > 0:
        return call_local(a - 1, b, c)
    else:
        return call_add_mult(a, b, c)

