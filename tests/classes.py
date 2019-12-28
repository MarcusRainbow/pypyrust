class Foo:
    def __init__(self, a: int, b: str):
        self.a = a
        self.b = b
        self.counter = 0

    def increment(self):
        self.counter += 1

    def add(self, x: int):
        self.counter += x

def create_foo(a: int, b: str) -> Foo:
    foo = Foo(a, b)
    return foo

def increment_foo(foo: Foo):
    was = foo.counter
    foo.increment()
    now = foo.counter
    assert(now == was + 1)

def add_foo(foo: Foo, x: int):
    was = foo.counter
    foo.add(x)
    now = foo.counter
    assert(now == was + x)

def examine_foo(foo: Foo):
    b = foo.b
    a = foo.a
    print("a = ", a, "b = ", b)

