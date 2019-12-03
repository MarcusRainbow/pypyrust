"""
The top-level compiler module for PyPyRust. It takes a Python source
file and generates a Rust source file, representing the Python.
"""

import ast
import sys
from enum import Enum

OPEN_BRACE = '{'
CLOSE_BRACE = '}'

def type_from_annotation(annotation: str, arg: str) -> str:
    if annotation is None:
        print("missing type annotation for argument '{arg}'", file=sys.stderr)
        return 'None'
    id = annotation.id
    if id == 'int':
        return 'u32'
    elif id == 'str':
        return 'str'
    elif id == 'num':
        return 'f64'
    else:
        print("unrecognised type annotation for argument '{arg}': '{annotation}'", file=sys.stderr)
        return annotation

class TreeWalker(ast.NodeVisitor):

    def __init__(self):
        self.indent = 0
        self.next_separator = ""

    def pretty(self):
        return '    ' * self.indent
    
    def add_pretty(self, increment: int):
        self.indent += increment

    def visit_FunctionDef(self, node):
        # function name
        print(f"{self.pretty()}fn {node.name}(", end='')

        # function arg list
        self.next_separator = ""
        self.generic_visit(node.args)

        # return value
        if node.returns is not None:
            typed = type_from_annotation(node.returns, "return")
            print(f") -> {typed} {OPEN_BRACE}")
        else:
            print(") {")        

        # body of the function
        self.add_pretty(1)
        for expr in node.body:
            self.visit(expr)
        self.add_pretty(-1)
        print(f"{self.pretty()}{CLOSE_BRACE}")
        print()

    def visit_arg(self, node):
        typed = type_from_annotation(node.annotation, node.arg)
        print(f"{self.next_separator}{node.arg} : {typed}", end='')
        self.next_separator = ", "
        # self.generic_visit(node)

    def visit_Expr(self, node):
        print(f"{self.pretty()}", end='')
        self.generic_visit(node)
        print(";")

    def visit_Return(self, node):
        print(f"{self.pretty()}return ", end='')
        self.generic_visit(node)
        print(";")

    def visit_Call(self, node):
        self.visit(node.func)
        print("(", end='')
        sep = ""
        for a in node.args:
            print(sep, end='')
            self.visit(a)
            sep = ", "
        print(")", end='')
        
    def visit_Name(self, node):
        print(f"{node.id}", end='')
        self.generic_visit(node)

    def visit_Str(self, node):
        print(f'"{node.s}"', end='')

    def visit_BinOp(self, node):
        self.generic_visit(node)
    
    def visit_Add(self, node):
        print(" + ", end='')
    
    def visit_Mult(self, node):
        print(" * ", end='')

def compile_to_rust(source, filename: str) -> bool:
    """
    Compiles a Python source file, generating Rust source in
    stdout that does the same thing. Warnings and compiler errors are
    sent to stderr. Returns a bool which is True if the compilation
    was successful (no errors, though there may have been warnings).

    source is typically a string, but other types are supported
    (see ast.parse).
    
    filename_in is only used for prettifying the error output.
    """

    # compile the python source into an AST
    tree = ast.parse(source, filename, 'exec')

    # Walk the tree, outputting Rust code as we go (rather like XSLT)
    TreeWalker().visit(tree)

    return True

def test_compiler(filename: str):
    file = open(filename, 'r')
    source = file.read()
    file.close()
    ok = compile_to_rust(source, filename)
    assert(ok)

if __name__ == "__main__":
    test_compiler("tests/hello_world.py")
    test_compiler("tests/add_mult.py")
