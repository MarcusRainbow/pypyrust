"""
Module containing the core components for outputting Rust code.
"""

import ast
import sys
from enum import Enum
import filecmp
import os
from typing import Dict, Tuple
from var_analyser import VariableAnalyser, FunctionHeaderFinder, \
    type_from_annotation, container_type_needed, get_node_path

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

    def __init__(self, return_types: Dict[str, str]):
        self.return_types = return_types
        self.indent = 0
        self.next_separator = ""
        self.precedence = 0
        self.in_aug_assign = False
        self.variables = set()
        self.mutable_vars = set()
        self.type_by_node = {}

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

    def visit_and_optionally_convert(self, node):
        conversion = container_type_needed(node, self.type_by_node)
        if conversion:
            self.precedence = MAX_PRECEDENCE * 2
            self.visit(node)
            print(conversion, end='')
        else:
            self.visit(node)

    def is_variable_mutable_declared(self, target) -> Tuple[bool, bool]:
        """
        Returns true if the variable is mutable, followed by
        true if the variable is already declared.
        """
        if isinstance(target, ast.Name):
            name = target.id
            mutable = name in self.mutable_vars
            declared = name in self.variables

            # if the variable is not yet declared, mark it as such
            # so we don't declare it twice
            if not declared:
                self.variables.add(name)

            return mutable, declared

        elif isinstance(target, Tuple):
            # if this is a tuple, all of the contained variables should
            # be declared or none of them. Treat them as mutable if any
            # need to be. Treat them as declared if any are (undeclared
            # variables will give rise to a Rust error).
            mutable, declared = False, False
            for element in target.elts:
                el_mut, el_dec = self.is_variable_mutable_declared(element)
                if el_mut:
                    mutable = True
                if el_dec:
                    declared = True
        else:
            # unrecognised type. Add a warning and continue
            print("Warning: unrecognised variable type", file=sys.stderr)
            return True, False

    def visit_FunctionDef(self, node):
        # Analyse the variables in this function to see which need
        # to be predeclared or marked as mutable
        analyser = VariableAnalyser(self.return_types)
        analyser.visit(node)
        self.type_by_node = analyser.get_type_by_node()

        # function name. Always public, as Python has no
        # private functions.
        print(f"{self.pretty()}pub fn {node.name}(", end='')

        # start with a clean set of variables 
        # (do we need to worry about nested functions?)
        self.variables.clear()
        self.mutable_vars = analyser.get_mutable_vars()

        # function arg list
        self.next_separator = ""
        self.generic_visit(node.args)

        # return value
        if node.returns is not None:
            typed = type_from_annotation(node.returns, "return", True)
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
        typed = type_from_annotation(node.annotation, node.arg, False)
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
        self.visit_and_optionally_convert(node.value)
        print(";")

    def visit_Call(self, node):
        node_path = get_node_path(node.func)
        if node_path and len(node_path) == 1:
            if node_path[0] == "print":
                return self.visit_Print(node)
            elif node_path[0] == "range":
                return self.visit_Range(node)

        # Function name, with namespacing if required. Note that if
        # any namespacing is required, we first need an initial
        # :: so we start from the global namespace.
        separator = "::" if len(node_path) > 1 else ""
        for name in node_path:
            print(separator, end='')
            print(name, end='')

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
                self.visit(node.args[0])

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
                self.visit(arg)

        print(")", end='')

    def visit_Range(self, node):
        """
        Not part of the standard visitor pattern, but internally
        special-cased, because Rust renders Python's range with
        special syntax.

        Python ranges come in three flavours, depending on the number
        of arguments, and they map to Rust as follows:

        1. range(a)         ->      0..a
        2. range(a, b)      ->      a..b
        3. range(a, b, c)   ->      (a..b).step_by(c)
        """
        n = len(node.args)
        if n == 1:
            print("0..", end='')
            self.visit(node.args[0])
        elif n == 2:
            self.visit(node.args[0])
            print("..", end='')
            self.visit(node.args[1])
        elif n == 3:
            print("(")
            self.visit(node.args[0])
            print("..", end='')
            self.visit(node.args[1])
            print(").step_by(")
            self.visit(node.args[2])
            print(")")

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

    def visit_Tuple(self, node):
        print("(", end='')
        separator = ""
        for element in node.elts:
            print(separator, end='')
            self.visit(element)
            separator = ", "
        print(")", end='')

    def visit_Index(self, node):
        print("[", end='')
        self.visit(node.value)
        print("]", end='')

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
        self.precedence = 0     # don't need params around if condition
        self.visit(node.test)
        print(" { ", end='')
        self.visit(node.body)
        print(" } else { ", end='')
        self.visit(node.orelse)
        print(" }", end='')

    def visit_If(self, node):
        print(f"{self.pretty()}if ", end='')
        self.precedence = 0     # don't need params around if condition
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
        self.precedence = 0     # don't need params around while condition
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
        self.precedence = 0     # don't need params around for condition
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
            mutable, declared = self.is_variable_mutable_declared(target)
            if declared:
                print(f"{self.pretty()}", end='')
            else:
                mut = "mut " if mutable else ""
                print(f"{self.pretty()}let {mut}", end='')

            self.visit(target)
            print(" = ", end='')
            if first:
                self.precedence = 0     # don't need params around value
                self.visit_and_optionally_convert(node.value)
                first_target = target
                first = False
            else:
                # only evaluate expression once
                self.visit(first_target)
            print(";")

    def visit_AnnAssign(self, node):
        """
        Hinted variable assignment statement, such as x: int = 42

        We do not yet handle non-simple assignments such as
        (x): int = 42
        """
        # treatment depends on whether it is the first time we
        # have seen this variable. (Do not use shadowing.)
        mutable, declared = self.is_variable_mutable_declared(node)
        if declared:
            print(f"{self.pretty()}", end='')
        else:
            mut = "mut " if mutable else ""
            print(f"{self.pretty()}let {mut}", end='')

        self.visit(node.target)
        typed = type_from_annotation(node.annotation, node.target, True)
        print(f": {typed} = ", end='')
        self.precedence = 0     # don't need params around value
        self.visit_and_optionally_convert(node.value)
        print(";")

    def visit_AugAssign(self, node):
        print(self.pretty(), end='')
        self.visit(node.target)
        self.in_aug_assign = True
        self.visit(node.op)
        self.in_aug_assign = False
        self.precedence = 0     # don't need params around value
        self.visit(node.value)
        print(";")

def test_compiler(filename: str):
    input_filename = f"tests/{filename}.py"
    output_filename = f"temp/{filename}.rs"
    baseline_filename = f"baseline/src/{filename}.rs"
    
    input_file = open(input_filename, 'r')
    source = input_file.read()
    input_file.close()

    # for var_analysis to be able to find the type hints for
    # functions in other modules, they must be on the path
    old_sys_path = sys.path
    sys.path.append("./tests")

    output_file = open(output_filename, 'w')
    old_stdout = sys.stdout
    sys.stdout = output_file
    tree = ast.parse(source, filename, 'exec')

    function_finder = FunctionHeaderFinder()
    function_finder.visit(tree)
    RustGenerator(function_finder.get_return_types()).visit(tree)
    output_file.close()
    sys.stdout = old_stdout

    sys.path = old_sys_path

    ok = (os.path.isfile(baseline_filename) and 
        filecmp.cmp(baseline_filename, output_filename, shallow=False))
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
    test_compiler("function_calls")
    test_compiler("tuples")

