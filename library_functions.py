"""
Definitions of standard library functions and methods, and their
conversions into Rust
"""

import sys
import ast
from var_analyser import is_iterator_type, is_reference_type

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

STANDARD_METHODS = {
    ("HashSet<_>", "add")  : lambda v, n: handle_refargs("insert", v, n),
    ("HashMap<_>", "get")  : lambda v, n: handle_get_or_default("get", v, n, True),
    ("HashMap<_>", "items"): lambda v, n: handle_items(v, n),
    ("HashMap<_>", "pop")  : lambda v, n: handle_get_or_default("remove", v, n, False),
    ("HashMap<_>", "popitem"): lambda v, n: handle_popitem(v, n),
    ("HashMap<_>", "setdefault"): lambda v, n: handle_set_default(v, n),
    ("HashMap<_>", "update"): lambda v, n: handle_update(v, n),
    ("Vec<_>", "append")   : lambda v, n: handle_method("push", v, n),
}

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

def handle_refargs(method_name: str, visitor, node):
    """
    Handle a method that takes reference args, such as insert
    """
    print(f".{method_name}(", end='')
    separator = ""
    for arg in node.args:
        print(separator, end='')
        add_reference_if_needed(visitor.type_by_node[arg])
        visitor.visit_and_optionally_convert(arg)
        separator = ", "
    
    print(")", end='')

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

STANDARD_FUNCTIONS = {
    "dict":  lambda visitor, node: handle_dict(visitor, node),
    "len":   lambda visitor, node: handle_len(visitor, node),
    "print": lambda visitor, node: handle_print(visitor, node),
    "range": lambda visitor, node: handle_range(visitor, node),
    "zip":   lambda visitor, node: handle_zip(visitor, node),
}

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
    equivalent in Rust is foo.size()
    """
    visitor.visit(node.args[0])
    print(".size()", end='')
