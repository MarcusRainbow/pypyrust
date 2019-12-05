"""
The top-level compiler module for PyPyRust. It takes a Python source
file and generates a Rust source file, representing the Python.
"""

import ast
import sys
from enum import Enum

OPEN_BRACE = '{'
CLOSE_BRACE = '}'
ALLOWED_BINARY_OPERATORS = { "Add", "Mult", "Sub", "Div", "FloorDiv",
    "Mod", "LShift", "RShift", "BitOr", "BitXor", "BitAnd" }
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

def type_from_annotation(annotation: str, arg: str) -> str:
    if annotation is None:
        print("missing type annotation for argument '{arg}'", file=sys.stderr)
        return 'None'
    id = annotation.id
    if id == 'int':
        return 'u32'
    elif id == 'bool':
        return 'bool'
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
        self.precedence = 0
        self.in_aug_assign = False
        self.variables = set()

    def pretty(self):
        return '    ' * self.indent
    
    def add_pretty(self, increment: int):
        self.indent += increment

    def print_operator(self, op: str):
        if self.in_aug_assign:
            print(f" {op}= ", end='')
        else:
            print(f" {op} ", end='')

    def parens_if_needed(self, op: str, visit):
        # use precedence * 2 so we can add one to control less than or equal
        prec = OPERATOR_PRECEDENCE[op] * 2
        if prec < self.precedence:
            print("(", end='')

        old_prec = self.precedence
        self.precedence = prec
        visit()
        self.precedence = old_prec

        if prec < self.precedence:
            print(")", end='')

    def visit_FunctionDef(self, node):
        # function name
        print(f"{self.pretty()}fn {node.name}(", end='')

        # start with a clean set of variables 
        # (do we need to worry about nested functions?)
        self.variables = set()

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

        # clean the set of variables. The names do not leak past here
        self.variables = set()

    def visit_arg(self, node):
        typed = type_from_annotation(node.annotation, node.arg)
        # We currently make all args mutable, as we do not know whether they
        # may be modified later. TODO add a first pass to find whether this is
        # needed.
        print(f"{self.next_separator}mut {node.arg}: {typed}", end='')
        self.variables.add(node.arg)
        self.next_separator = ", "

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

    def visit_NameConstant(self, node):
        val = node.value
        if val in REPLACE_CONSTANTS:
            val = REPLACE_CONSTANTS[node.value]
        print(f"{val}", end='')

    def visit_Str(self, node):
        print(f'"{node.s}"', end='')

    def visit_Num(self, node):
        print(f"{node.n}", end='')

    def visit_BinOp(self, node):
        # some binary operators such as '+' translate
        # into binary operators in Rust
        op = node.op.__class__.__name__
        if op in ALLOWED_BINARY_OPERATORS:
            self.parens_if_needed(op, lambda: self.do_visit_BinOp(node))
        else:
            old_prec = self.precedence
            self.precedence = 0     # these parentheses reset everything

            self.visit(node.op)
            print("(", end='')
            self.visit(node.left)
            print(", ", end='')
            self.visit(node.right)
            print(")", end='')

            self.precedence = old_prec
    
    def do_visit_BinOp(self, node):
        self.visit(node.left)
        self.visit(node.op)
        self.precedence += 1    # left to right associative
        self.visit(node.right)
        self.precedence -= 1

    def visit_Add(self, node):
        self.print_operator("+")
    
    def visit_Mult(self, node):
        self.print_operator("*")

    def visit_Sub(self, node):
        self.print_operator("-")
    
    def visit_Div(self, node):
        # print("warning: floating point division", file=sys.stderr)
        self.print_operator("/")

    def visit_FloorDiv(self, node):
        # print("warning: integer division", file=sys.stderr)
        self.print_operator("/")

    def visit_Mod(self, node):
        # print("warning: Python mod operator is different from Rust")
        self.print_operator("%")

    def visit_Pow(self, node):
        print("pow", end='')

    def visit_LShift(self, node):
        self.print_operator("<<")

    def visit_RShift(self, node):
        self.print_operator(">>")

    def visit_BitOr(self, node):
        self.print_operator("|")

    def visit_BitXor(self, node):
        self.print_operator("^")

    def visit_BitAnd(self, node):
        self.print_operator("&")
    
    def visit_UnaryOp(self, node):
        op = node.op.__class__.__name__
        self.parens_if_needed(op, lambda: self.generic_visit(node))

    def visit_UAdd(self, node):
        print("+", end='')

    def visit_USub(self, node):
        print("-", end='')

    def visit_Not(self, node):
        print("!", end='')

    def visit_Invert(self, node):
        print("~", end='')

    def visit_BoolOp(self, node):
        op = node.op.__class__.__name__
        self.parens_if_needed(op, lambda: self.do_visit_BoolOp(node))

    def do_visit_BoolOp(self, node):
        """
        Invoked by visit_BoolOp to do the work apart from the parens
        """
        first = True
        for v in node.values:
            if not first:
                self.visit(node.op)
            self.visit(v)
            first = False

    def visit_And(self, node):
        print(" && ", end='')

    def visit_Or(self, node):
        print(" || ", end='')

    def visit_Compare(self, node):
        """
        Invoked for any comparison operator such as <, >, ==.

        Note that multiple comparisons in Rust are very different from
        Python. In Rust, it is not permissible to write "a X b Y c"
        where X and Y are comparison operators (possibly the same one).
        In Python, this is shorthand for "(a X b) and (b Y c). We
        therefore expand it like this in the Rust.
        """
        op_len = len(node.ops)
        assert(op_len == len(node.comparators))
        if op_len > 1:
            print("(", end='')

        self.visit(node.left)
        for op, c, i in zip(node.ops, node.comparators, range(op_len)):
            # we do not yet handle is or in
            assert(op.__class__.__name__ in ALLOWED_COMPARISON_OPERATORS)
            self.visit(op)
            self.visit(c)
            if op_len > 1:
                if i != op_len - 1:
                    print(") && (", end='')
                    self.visit(c)
                else:
                    print(")", end='')

    def visit_Eq(self, node):
        print(" == ", end='')
    
    def visit_NotEq(self, node):
        print(" != ", end='')

    def visit_Lt(self, node):
        print(" < ", end='')
    
    def visit_LtE(self, node):
        print(" <= ", end='')

    def visit_Gt(self, node):
        print(" > ", end='')
    
    def visit_GtE(self, node):
        print(" >= ", end='')

    def visit_IfExp(self, node):
        print("if ", end='')
        self.visit(node.test)
        print(" { ", end='')
        self.visit(node.body)
        print(" } else { ", end='')
        self.visit(node.orelse)
        print(" }", end='')

    def visit_If(self, node):
        print(f"{self.pretty()}if ", end='')
        self.visit(node.test)
        print(" {")
        self.add_pretty(1)
        for line in node.body:
            self.visit(line)
        self.add_pretty(-1)
        if node.orelse:
            print(f"{self.pretty()}{CLOSE_BRACE} else {OPEN_BRACE}")
            self.add_pretty(1)
            for line in node.orelse:
                self.visit(line)
            self.add_pretty(-1)
        print(f"{self.pretty()}{CLOSE_BRACE}")

    def visit_While(self, node):
        print(f"{self.pretty()}while ", end='')
        self.visit(node.test)
        print(" {")
        self.add_pretty(1)
        for line in node.body:
            self.visit(line)
        self.add_pretty(-1)
        assert(len(node.orelse) == 0)
        print(f"{self.pretty()}{CLOSE_BRACE}")
    
    def visit_For(self, node):
        print(f"{self.pretty()}for ", end='')
        self.visit(node.target)
        print(" in ", end='')
        self.visit(node.iter)
        print(" {")
        self.add_pretty(1)
        for line in node.body:
            self.visit(line)
        self.add_pretty(-1)
        assert(len(node.orelse) == 0)
        print(f"{self.pretty()}{CLOSE_BRACE}")
    
    def visit_Break(self, node):
        print(f"{self.pretty()}break;")

    def visit_Continue(self, node):
        print(f"{self.pretty()}continue;")

    def visit_Assign(self, node):
        """
        Variable assignment statement, such as x = y = 42

        Note that Rust does not handle multiple assignments on one
        line, so we write a line for each one.

        Currently we generate a mutable Rust variable, because we
        do not know whether it will be later assigned to. We could
        do a first pass with a visitor to determine the lifecycle
        of variables, which would allow us to tighten up the
        assignments.

        We always assign mutable, see visit_Assign for reasons.
        """
        first = True
        for target in node.targets:
            # treatment depends on whether it is the first time we
            # have seen this variable. (Do not use shadowing.)
            name = target.id
            if name in self.variables:
                print(f"{self.pretty()}", end='')
            else:
                print(f"{self.pretty()}let mut ", end='')
                self.variables.add(name)

            self.visit(target)
            print(" = ", end='')
            if first:
                self.visit(node.value)
                first = False
            else:
                # only evaluate expression once
                self.visit(target)
            print(";")

    def visit_AnnAssign(self, node):
        """
        Hinted variable assignment statement, such as x: int = 42

        We do not yet handle non-simple assignments such as
        (x): int = 42
        """
        # treatment depends on whether it is the first time we
        # have seen this variable. (Do not use shadowing.)
        name = node.target.id
        if name in self.variables:
            print(f"{self.pretty()}", end='')
        else:
            print(f"{self.pretty()}let mut ", end='')
            self.variables.add(name)

        self.visit(node.target)
        typed = type_from_annotation(node.annotation, node.target)
        print(f": {typed} = ", end='')
        self.visit(node.value)
        print(";")

    def visit_AugAssign(self, node):
        print(self.pretty(), end='')
        self.visit(node.target)
        self.in_aug_assign = True
        self.visit(node.op)
        self.in_aug_assign = False
        self.visit(node.value)
        print(";")

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
    test_compiler("tests/flow_of_control.py")
    test_compiler("tests/variables.py")
