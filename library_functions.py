"""
Definitions of standard library functions and methods, and their
conversions into Rust
"""

import sys
import ast
from var_utils import is_iterator_type, is_reference_type, \
    dict_type_from_list, strip_container, detemplatise, \
    extract_types, UNKNOWN_TYPE

ALLOWED_COMPARISON_OPERATORS = { "Eq", "NotEq", "Lt", "LtE", "Gt", "GtE" }

REPLACE_CONSTANTS = {
    True : "true",
    False : "false",
} 

# Fortunately, the precedence of Python operators is the same as Rust,
# except for ** (doesn't exist in Rust), is/in (don't exist in Rust)
# "not", which is very highest precedence in Rust, but just above the
# other boolean operators in Rust.
OPERATOR_PRECEDENCE = {
    "Pow": 12,
    "UAdd": 11, "USub": 11, "Invert": 11, "Not": 11,
    "Mult": 10, "Div": 10, "FloorDiv": 10, "Mod": 10,
    "Add": 9, "Sub": 9,
    "LShift": 8, "RShift": 8,
    "BitAnd": 7,
    "BitXor": 6,
    "BitOr": 5,
    "Eq": 4, "NotEq": 4, "Gt": 4, "GtE": 4, "Lt": 4, "LtE": 4,
    # "Not": 3, (this would be right for Python, but not for Rust)
    "And": 2,
    "Or": 1,
}
# One bigger than any actual precedence. Use this to force parentheses
MAX_PRECEDENCE = 13

STANDARD_METHOD_RETURNS = {
    ("HashMap<_>", "keys"):    lambda types: f"[{types[0]}]",
    ("HashMap<_>", "values"):  lambda types: f"[{types[1]}]",
    ("HashMap<_>", "items"):   lambda types: f"[({types[0]}, {types[1]})]",
    ("HashMap<_>", "get"):     lambda types: f"&{types[1]}",
    ("HashMap<_>", "clear"):   lambda types: "()",
    ("HashMap<_>", "update"):  lambda types: "()",
    ("HashMap<_>", "pop"):     lambda types: types[1],
    ("HashMap<_>", "popitem"): lambda types: f"({types[0]}, {types[1]})",
    ("HashMap<_>", "setdefault"):   lambda types: f"&{types[1]}",
    ("HashSet<_>", "add"):          lambda types: "()",
    ("HashSet<_>", "clear"):        lambda types: "()",
    ("HashSet<_>", "copy"):         lambda types: f"HashSet<{types[0]}>",
    ("HashSet<_>", "difference"):   lambda types: f"HashSet<{types[0]}>",
    ("HashSet<_>", "difference_update"): lambda types: "()",
    ("HashSet<_>", "discard"):      lambda types: "()",
    ("HashSet<_>", "intersection"): lambda types: f"HashSet<{types[0]}>",
    ("HashSet<_>", "intersection_update"): lambda types: "()",
    ("HashSet<_>", "isdisjoint"):   lambda types: "bool",
    ("HashSet<_>", "issubset"):     lambda types: "bool",
    ("HashSet<_>", "issuperset"):   lambda types: "bool",
    ("HashSet<_>", "remove"):       lambda types: "()",
    ("HashSet<_>", "symmetric_difference"):        lambda types: f"HashSet<{types[0]}>",
    ("HashSet<_>", "symmetric_difference_update"): lambda types: "()",
    ("HashSet<_>", "union"):        lambda types: f"HashSet<{types[0]}>",
    ("HashSet<_>", "union_update"): lambda types: "()",
    ("Vec<_>", "append"):      lambda types: "()",
    ("Vec<_>", "insert"):      lambda types: "()",
    ("Vec<_>", "extend"):      lambda types: "()",
    ("Vec<_>", "index"):       lambda types: "i64",
    ("Vec<_>", "sum"):         lambda types: types[0],
    ("Vec<_>", "count"):       lambda types: "i64",
    ("Vec<_>", "min"):         lambda types: types[0],
    ("Vec<_>", "max"):         lambda types: types[0],
    ("Vec<_>", "reverse"):     lambda types: "()",
    ("Vec<_>", "sort"):        lambda types: "()",
    ("Vec<_>", "pop"):         lambda types: types[0],
}

STANDARD_METHODS = {
    ("HashMap<_>", "get")  :   lambda v, n: handle_get_or_default("get", v, n, True),
    ("HashMap<_>", "items"):   lambda v, n: handle_items(v, n),
    ("HashMap<_>", "pop")  :   lambda v, n: handle_get_or_default("remove", v, n, False),
    ("HashMap<_>", "popitem"): lambda v, n: handle_popitem(v, n),
    ("HashMap<_>", "setdefault"): lambda v, n: handle_set_default(v, n),
    ("HashMap<_>", "update"):  lambda v, n: handle_update(v, n),
    ("HashSet<_>", "add")  :   lambda v, n: handle_method("insert", v, n),
    ("HashSet<_>", "clear"):   lambda v, n: handle_method("clear", v, n),
    ("HashSet<_>", "copy"):    lambda v, n: handle_method("clone", v, n),
    ("HashSet<_>", "difference"):   lambda v, n: handle_collect("difference", v, n),
    ("HashSet<_>", "difference_update"): lambda v, n: handle_todo("difference_update", v, n),
    ("HashSet<_>", "discard"):      lambda v, n: handle_refargs("remove", v, n),
    ("HashSet<_>", "intersection"): lambda v, n: handle_collect("intersection", v, n),
    ("HashSet<_>", "intersection_update"): lambda v, n: handle_todo("intersection_update", v, n),
    ("HashSet<_>", "isdisjoint"):   lambda v, n: handle_refargs("is_disjoint", v, n),
    ("HashSet<_>", "issubset"):     lambda v, n: handle_refargs("is_subset", v, n),
    ("HashSet<_>", "issuperset"):   lambda v, n: handle_refargs("is_superset", v, n),
    ("HashSet<_>", "remove"):       lambda v, n: handle_refargs("remove", v, n),
    ("HashSet<_>", "symmetric_difference"): lambda v, n: handle_collect("symmetric_difference", v, n),
    ("HashSet<_>", "symmetric_difference_update"): lambda v, n: handle_todo("symmetric_difference_update", v, n),
    ("HashSet<_>", "union"):        lambda v, n: handle_collect("union", v, n),
    ("HashSet<_>", "union_update"): lambda v, n: handle_method("union_update", v, n),
    ("Vec<_>", "append")   :   lambda v, n: handle_method("push", v, n),
    ("Vec<_>", "insert"):      lambda v, n: handle_method("insert", v, n),
    ("Vec<_>", "extend"):      lambda v, n: handle_method("extend", v, n),
    ("Vec<_>", "index"):       lambda v, n: handle_index(v, n),
    ("Vec<_>", "sum"):         lambda v, n: handle_sum(v, n),
    ("Vec<_>", "count"):       lambda v, n: handle_count(v, n),
    ("Vec<_>", "min"):         lambda v, n: handle_iter_method_unwrapped("min", v, n),
    ("Vec<_>", "max"):         lambda v, n: handle_iter_method_unwrapped("max", v, n),
    ("Vec<_>", "reverse"):     lambda v, n: handle_method("reverse", v, n),
    ("Vec<_>", "sort"):        lambda v, n: handle_method("sort", v, n),
    ("Vec<_>", "pop"):         lambda v, n: handle_method_unwrapped("pop", v, n),
}

# Mapping from Python function name to Rust return type
STANDARD_FUNCTION_RETURNS = {
    "dict":  lambda args: dict_type_from_list(args[0]),
    "print": lambda args: "()",
    "range": lambda args: f"[{args[0]}]",
    "zip":   lambda args: f"[({', '.join([ strip_container(x) for x in args ])})]",
    "len":   lambda args: "i64",
}

STANDARD_FUNCTIONS = {
    "dict":  lambda visitor, node: handle_dict(visitor, node),
    "len":   lambda visitor, node: handle_len(visitor, node),
    "print": lambda visitor, node: handle_print(visitor, node),
    "range": lambda visitor, node: handle_range(visitor, node),
    "zip":   lambda visitor, node: handle_zip(visitor, node),
}

def method_return_type(class_type: str, method_name: str) -> str:
    """
    Given the name of a class and a method on the class, return
    the return type of the method.
    """
    method = (detemplatise(class_type), method_name)
    if method not in STANDARD_METHOD_RETURNS:
        return UNKNOWN_TYPE

    types = extract_types(class_type)
    return STANDARD_METHOD_RETURNS[method](types)

def handle_method(method_name: str, visitor, node):
    """
    Handle a method that takes args that may need a to_string, such as push
    """
    print(f".{method_name}(", end='')
    separator = ""
    for arg in node.args:
        print(separator, end='')
        visitor.visit_and_optionally_convert(arg)
        separator = ", "
    
    print(")", end='')

def handle_todo(method_name: str, visitor, node):
    """
    Handle a method that is not currently supported, for example
    because there is no equivalent in Rust.

    Replace it with the "clear" method, which at least ensures
    the Rust clean compiles and does not return unwanted data.
    """
    print(f"Warning: there is no Rust equivalent of {method_name}", file=sys.stderr)
    print(".clear();")
    print(f"{visitor.pretty()}// TODO {method_name}(", end='')
    separator = ""
    for arg in node.args:
        print(separator, end='')
        visitor.visit_and_optionally_convert(arg)
        separator = ", "
    print(")", end='')

def handle_method_unwrapped(method_name: str, visitor, node):
    handle_method(method_name, visitor, node)
    print(".unwrap()", end='')

def handle_iter_method(method_name: str, visitor, node):
    print_iter_if_needed(visitor.type_by_node[node.func])
    handle_method(method_name, visitor, node)

def handle_iter_method_unwrapped(method_name: str, visitor, node):
    handle_iter_method(method_name, visitor, node)
    print(".unwrap()", end='')

def handle_refargs(method_name: str, visitor, node):
    """
    Handle a method that takes reference args, such as insert
    """
    print(f".{method_name}(", end='')
    separator = ""
    for arg in node.args:
        print(separator, end='')
        add_reference_if_needed(visitor.type_by_node[arg])
        visitor.visit(arg)
        separator = ", "
    
    print(")", end='')

def handle_collect(method_name: str, visitor, node):
    """
    Handle a method that takes reference args and returns an
    iterator that must be collected, such as intersection.
    """
    print(f".{method_name}(", end='')
    separator = ""
    for arg in node.args:
        print(separator, end='')
        add_reference_if_needed(visitor.type_by_node[arg])
        visitor.visit_and_optionally_convert(arg)
        separator = ", "

    typed = visitor.type_by_node[node.func]
    print(f").cloned().collect::<{typed}>()", end='')

def handle_get_or_default(method_name: str, visitor, node, returns_ref: bool):
    """
    Handle a method on a Map that returns either a value from
    the map or a default value.
    """
    print(f".{method_name}(", end='')
    add_reference_if_needed(visitor.type_by_node[node.args[0]])
    visitor.visit(node.args[0])
    print(").unwrap_or(", end='')
    if returns_ref:
        # note we should always add a reference (&) as 
        # visit_and_optionally_convert always converts a reference
        print("&", end='')
    visitor.visit_and_optionally_convert(node.args[1])
    print(")", end='')

def handle_set_default(visitor, node):
    """
    In Python, set_default returns the value associated with the
    given key if it is in the dictionary. Otherwise it adds the
    given default value to the dictionary and returns that.

    In Rust, the entry() method returns an optional value, and
    or_insert optionally inserts its argument. This does the
    same as Python, though more flexibly.
    """
    print(".entry(", end='')
    add_reference_if_needed(visitor.type_by_node[node.args[0]])
    visitor.visit_and_optionally_convert(node.args[0])
    print(").or_insert(", end='')
    visitor.visit_and_optionally_convert(node.args[1])
    print(")", end='')

def add_reference_if_needed(typed: str):
    """
    Adds a & character to make a reference if needed.
    """    
    if not is_reference_type(typed):
        print("&", end='')

def print_iter_if_needed(typed: str):
    """
    If the given type is not already an iterator, invoke
    .iter() to make one
    """
    if not is_iterator_type(typed):
        print(".iter()", end='')

def handle_items(visitor, node):
    """
    Returns an iterator to a (key, value) pair. In Rust this is tricky
    because iter() returns an iterator to (&key, &value) so we need
    to convert this.

    This is an example of a place where Rust is really hard to handle
    because of its rules about borrowing, and the lack of overloaded
    functions.
    """
    print(".iter().map(|(ref k, ref v)| ((*k).clone(), (*v).clone()))", end='')

def handle_popitem(visitor, node):
    """
    In Python returns some arbitrary (key, value) pair, which is removed.

    Rust has a similar remove_entry, but this requires a key. We use
    drain, which returns an iterator, and just take the first entry.

    If the iterator is exhausted, in other words there are no more elements,
    Rust like Python just panics. (Why is this sensible behaviour?)
    """
    print(".drain().next().unwrap()", end='')

def handle_update(visitor, node):
    """
    In Python, update takes an iterator yielding (key, value) pairs
    or a dictionary, and adds them all to self. The equivalent in
    Rust is extend.
    """
    print(".extend(", end='')
    visitor.visit(node.args[0])
    print_iter_if_needed(visitor.type_by_node[node.args[0]])
    print(")", end='')

def handle_count(visitor, node):
    """
    In Python, the count method counts the number of items in
    a container matching a given value. In Rust, count just
    counts all the items in the container, so we filter it first.
    """
    print_iter_if_needed(visitor.type_by_node[node.func])
    print(".filter(|&x| x == ", end='')
    visitor.visit(node.args[0])
    print(").count()", end='')

def handle_sum(visitor, node):
    """
    We can nearly handle sum as handle_iter_method("sum", v, n)
    but Rust requires the type.
    """
    print_iter_if_needed(visitor.type_by_node[node.func])
    typed = visitor.type_by_node[node]
    print(f".sum::<{typed}>()", end='')

def handle_index(visitor, node):
    """
    In Python, index returns the integer position of the
    given item, or raises an exception if not there. In
    Rust, we handle this with a position, panicking if
    the item doesn't exist.
    """
    print_iter_if_needed(visitor.type_by_node[node.func])
    if is_reference_type(visitor.type_by_node[node.args[0]]):
        print(".position(|ref x| *x == ", end='')
    else:
        print(".position(|&x| x == ", end='')
    visitor.visit(node.args[0])
    print(").unwrap()", end='')

def handle_dict(visitor, node):
    """
    Python's dict method creates a dictionary from a source of
    (key, value) tuples. The equivalent Rust is a method on
    an iterator, collect.
    """
    visitor.precedence = MAX_PRECEDENCE * 2    # make sure we put brackets if needed
    assert(len(node.args) == 1)
    visitor.visit(node.args[0])
    print_iter_if_needed(visitor.type_by_node[node.args[0]])
    print(".collect::<HashMap<_, _>>()", end='')

def handle_print(visitor, node):
    """
    Rust print is quite different from Python.
    """
    # Detect end= and sep= overrides. We assume that they
    # are only overridden by constants
    endline = None
    sep = " "
    for k in node.keywords:
        if k.arg == "end":
            endline = ast.literal_eval(k.value)
        elif k.arg == "sep":
            sep = ast.literal_eval(k.value)
    
    # use println if there is a carriage return at the end
    if endline is None or endline == '\n':
        print("println!(", end='')
        suffix = ""
    else:
        print("print!(", end='')
        suffix = endline
    
    # Of there is only one or zero argument and no suffix, just print it
    n = len(node.args)
    if n <= 1 and suffix == "":
        if n == 1:
            visitor.visit(node.args[0])

    # Otherwise, construct a format string, followed by the arguments.
    # We assume the first arg is not a c-style format string. 
    else:
        separator = ""
        fmt = ""
        for _ in range(n):
            fmt += separator
            separator = sep
            fmt += "{}"
        fmt += suffix
        # What we are trying to do here is to replace characters like
        # carriage return or tab with their escaped equivalents.
        # The trouble with repr is that it encloses the string in
        # single quotes, so we have to replace those with double.
        print(f'"{repr(fmt)[1:-1]}"', end='')

        for arg in node.args:
            print(", ", end='')
            visitor.visit(arg)

    print(")", end='')

def handle_range(visitor, node):
    """
    Rust renders Python's range with special syntax.

    Python ranges come in three flavours, depending on the number
    of arguments, and they map to Rust as follows:

    1. range(a)         ->      0..a
    2. range(a, b)      ->      a..b
    3. range(a, b, c)   ->      (a..b).step_by(c)
    """
    want_paren = visitor.precedence > 0

    n = len(node.args)
    if n == 1:
        if want_paren: print("(", end='')
        print("0..", end='')
        visitor.visit(node.args[0])
        if want_paren: print(")", end='')
    elif n == 2:
        if want_paren: print("(", end='')
        visitor.visit(node.args[0])
        print("..", end='')
        visitor.visit(node.args[1])
        if want_paren: print(")", end='')
    elif n == 3:
        print("(")
        visitor.visit(node.args[0])
        print("..", end='')
        visitor.visit(node.args[1])
        print(").step_by(")
        visitor.visit(node.args[2])
        print(")")

def handle_zip(visitor, node):
    """
    Rust's zip function is a method
    on an iterator, rather than a global function.

    We also need to force the iterator to be an iterator with
    an "iter" method, as the normal rules you'd get in a for
    loop do not apply.
    """
    # Really hard to handle more than two args to a zip in
    # Rust, though there are third party libraries that do.
    if len(node.args) != 2:
        raise Exception("We currently only handle zip with two args")

    visitor.precedence = MAX_PRECEDENCE * 2    # make sure we put brackets if needed
    visitor.visit(node.args[0])
    print(".iter().cloned().zip(", end='')
    visitor.visit(node.args[1])
    print(".iter().cloned())", end='')

def handle_len(visitor, node):
    """
    In Python, len(foo) returns the number of items in foo. The
    equivalent in Rust is foo.len()
    """
    visitor.visit(node.args[0])
    print(".len()", end='')
