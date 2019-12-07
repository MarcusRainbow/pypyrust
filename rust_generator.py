"""
Module containing the core components for outputting Rust code.
"""

import ast
import sys
from enum import Enum
import filecmp
import os
from var_analyser import VariableAnalyser, type_from_annotation

OPEN_BRACE = '{'
CLOSE_BRACE = '}'
# ALLOWED_BINARY_OPERATORS = { "Add", "Mult", "Sub", "Div", "FloorDiv",
#     "Mod", "LShift", "RShift", "BitOr", "BitXor", "BitAnd" }

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

class RustGenerator(ast.NodeVisitor):
    """
    Visitor of the Python AST which generates Rust code, streaming
    it out to stdout.
    """

    def __init__(self):
        self.indent = 0
        self.next_separator = ""
        self.precedence = 0
        self.in_aug_assign = False
        self.variables = set()
        self.mutable_vars = set()

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
        # Analyse the variables in this function to see which need
        # to be predeclared or marked as mutable
        analyser = VariableAnalyser()
        analyser.visit(node)

        # function name
        print(f"{self.pretty()}fn {node.name}(", end='')

        # start with a clean set of variables 
        # (do we need to worry about nested functions?)
        self.variables.clear()
        self.mutable_vars = analyser.get_mutable_vars()

        # function arg list
        self.next_separator = ""
        self.generic_visit(node.args)

        # return value
        if node.returns is not None:
            typed = type_from_annotation(node.returns, "return")
            print(f") -> {typed} {OPEN_BRACE}")
        else:
            print(") {")        

        self.add_pretty(1)

        # start with any variable declarations
        for (var, typed, default) in analyser.get_predeclared_vars():
            self.variables.add(var)
            print(f"{self.pretty()}let mut {var}: {typed} = {default};")

        # body of the function
        for expr in node.body:
            self.visit(expr)
        self.add_pretty(-1)
        print(f"{self.pretty()}{CLOSE_BRACE}")
        print()

        # clean the set of variables. The names do not leak past here
        self.variables.clear()

    def visit_arg(self, node):
        typed = type_from_annotation(node.annotation, node.arg)
        mutable = "mut " if node.arg in self.mutable_vars else ""
        print(f"{self.next_separator}{mutable}{node.arg}: {typed}", end='')
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
        if node.func.id == "print":
            self.visit_Print(node)
        else:
            self.visit(node.func)
            print("(", end='')
            sep = ""
            for a in node.args:
                print(sep, end='')
                self.visit(a)
                sep = ", "
            print(")", end='')

    def visit_Print(self, node):
        """
        Not part of the standard visitor pattern, but internally
        special-cased, because Rust print is quite different from
        Python.
        """
        # detect end= override
        endline = None
        sep = None
        for k in node.keywords:
            if k.arg == "end":
                endline = k.value
            elif k.arg == "sep":
                sep = k.value
        
        n = len(node.args)
        if n == 0:
            if not endline:
                print("println!();")
        else:
            for i, arg in enumerate(node.args):
                if i != 0:
                    print("print!(", end='')
                    if sep:
                        self.visit(sep)
                    else:
                        print('" "', end='')
                    print(");")
                if i == n - 1 and not endline:
                    print("println!(", end='')
                else:
                    print("print!(", end='')
                self.visit(arg)
                print(");")
            # for now, we assume that the override sets end to ''

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
        # into binary operators in Rust. However, pow needs
        # special handling.
        op = node.op.__class__.__name__
        if op == "Pow":
            self.visit_PowOp(node)
        else:
            self.parens_if_needed(op, lambda: self.do_visit_BinOp(node))
    
    def do_visit_BinOp(self, node):
        self.visit(node.left)
        self.visit(node.op)
        self.precedence += 1    # left to right associative
        self.visit(node.right)
        self.precedence -= 1

    def visit_PowOp(self, node):
        """
        Not a standard visitor function, but one we invoke
        to handle the Pow operator "**"
        """
        # ensure that any contained expression gets wrapped in
        # parentheses
        old_prec = self.precedence
        self.precedence = MAX_PRECEDENCE * 2

        # TODO decide between pow, powf and powi on the basis of type
        # For now, assume the arguments are integer (i64). Note that
        # Rust requires the rhs to be unsigned.
        self.visit(node.left)
        print(".pow((", end='')
        self.precedence = 0     # already have parentheses
        self.visit(node.right)
        print(") as u32)", end='')

        self.precedence = old_prec

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

    # def visit_Pow(self, node):
    #     print("pow", end='')

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
        """
        There is no unary addition operator in Rust. Just omit it
        as it is a no-op
        """
        pass

    def visit_USub(self, node):
        print("-", end='')

    def visit_Not(self, node):
        print("!", end='')

    def visit_Invert(self, node):
        """
        In Python the bitwise inversion operator "~" is distinct
        from boolean negation. This is not the case in Rust.
        """
        print("!", end='')

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
        """
        first = True
        for target in node.targets:
            # treatment depends on whether it is the first time we
            # have seen this variable. (Do not use shadowing.)
            name = target.id
            if name in self.variables:
                print(f"{self.pretty()}", end='')
            else:
                mutable = "mut " if name in self.mutable_vars else ""
                print(f"{self.pretty()}let {mutable}", end='')
                self.variables.add(name)

            self.visit(target)
            print(" = ", end='')
            if first:
                self.visit(node.value)
                first_name = name
                first = False
            else:
                # only evaluate expression once
                print(f" = {first_name}", end='')
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
            mutable = "mut " if name in self.mutable_vars else ""
            print(f"{self.pretty()}let {mutable}", end='')
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

def test_compiler(filename: str):
    input_filename = f"tests/{filename}.py"
    output_filename = f"temp/{filename}.ru"
    baseline_filename = f"baseline/{filename}.ru"
    
    input_file = open(input_filename, 'r')
    source = input_file.read()
    input_file.close()

    output_file = open(output_filename, 'w')
    old_stdout = sys.stdout
    sys.stdout = output_file
    tree = ast.parse(source, filename, 'exec')
    RustGenerator().visit(tree)
    output_file.close()
    sys.stdout = old_stdout

    ok = filecmp.cmp(baseline_filename, output_filename, shallow=False)
    if ok:
        print(f"test {filename} succeeded")
        os.remove(output_filename)
    else:
        print(f"test {filename} failed. Output file {output_filename} left in place.")

if __name__ == "__main__":
    test_compiler("hello_world")
    test_compiler("add_mult")
    test_compiler("flow_of_control")
    test_compiler("variables")
