"""
Module containing the core components for outputting Rust code.
"""

import ast
import sys
from enum import Enum
import filecmp
import os
from typing import Dict, Tuple, List
from var_analyser import VariableAnalyser, FunctionHeaderFinder, \
    type_from_annotation, container_type_needed, get_node_path, is_list, \
    detemplatise, extract_container, is_reference_type, is_iterator_type, \
    FunctionHeader, is_dict
from dependency_analyser import DependencyAnalyser
from library_functions import STANDARD_METHODS, STANDARD_FUNCTIONS, \
    print_iter_if_needed, add_reference_if_needed, \
    OPERATOR_PRECEDENCE, MAX_PRECEDENCE, \
    REPLACE_CONSTANTS, ALLOWED_COMPARISON_OPERATORS

OPEN_BRACE = '{'
CLOSE_BRACE = '}'
# ALLOWED_BINARY_OPERATORS = { "Add", "Mult", "Sub", "Div", "FloorDiv",
#     "Mod", "LShift", "RShift", "BitOr", "BitXor", "BitAnd" }

def target_as_string(node) -> str:
    """
    Given a node that is either a Tuple or a Name, return
    a representation as a string
    """
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Tuple):
        result = "("
        # separator = "&"         # iterator returns references. Convert these to values
        separator = ""
        for element in node.elts:
            result += separator
            result += target_as_string(element)
            # separator = ", &"
            separator = ", "
        result += ")"
        return result
    else:
        raise Exception("We only support tuples and names as the target of comprehensions")

class RustGenerator(ast.NodeVisitor):
    """
    Visitor of the Python AST which generates Rust code, streaming
    it out to stdout.
    """

    def __init__(self, headers: Dict[str, FunctionHeader]):
        self.headers = headers
        self.indent = 0
        self.next_separator = ""
        self.precedence = 0
        self.in_aug_assign = False
        self.variables = set()
        self.mutable_vars = set()
        self.mutable_ref_vars = set()
        self.type_by_node = {}
        self.target = ""
        self.unpacking = False

    def pretty(self):
        return '    ' * self.indent
    
    def add_pretty(self, increment: int):
        self.indent += increment

    def temp_variable(self):
        """
        Returns a string that can safely be used as a
        temp variable name
        """
        name = "tmp"
        i = 0
        while name in self.variables:
            name = f"tmp{i}"
            i += 1
        
        # make sure we don't use this one again
        self.variables.add(name)
        return name

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

    def sex_variable(self, target) -> Tuple[bool, bool, bool, bool]:
        """
        Finds out how a variable is to be treated in an
        assignment. Returns three bools:

        1. Is the variable mutable?
        2. Is the variable already declared?
        3. Is the variable suitable for assignment?
        4. Is this assignment of a dictionary item?

        If the variable is not already declared this function returns
        true in its second return value, but internally sets the 
        declared flag, as the variable is about to be declared.

        Rust, for some perverse reason, does not allow assignment of
        tuples in the form a, b = foo(). For example, the standard
        Python way to swap two variables is not legal Rust. As a
        result, we may need to use a temp variable.
        """
        if isinstance(target, ast.Name):
            name = target.id
            mutable = name in self.mutable_vars or name in self.mutable_ref_vars
            declared = name in self.variables
            assignable = True

            # if the variable is not yet declared, mark it as such
            # so we don't declare it twice
            if not declared:
                self.variables.add(name)

            return mutable, declared, assignable, False

        elif isinstance(target, ast.Tuple):
            # if this is a tuple, all of the contained variables should
            # be declared or none of them. Treat them as mutable if any
            # need to be. Treat them as declared if any are (undeclared
            # variables will give rise to a Rust error).
            # 
            mutable, declared = False, False
            for element in target.elts:
                el_mut, el_dec, _, el_dict = self.sex_variable(element)
                if el_mut:
                    mutable = True
                if el_dec:
                    declared = True
                if el_dict:
                    print("Warning: Rust cannot handle assignment into dictionary entries", sys.stderr)
            return mutable, declared, False, False

        elif isinstance(target, ast.Subscript):
            # If the target of the assignment is an element from a tuple
            # or list (e.g. a[3] = 42) we assume the target is mutable and
            # declared.
            isdict = (target.value in self.type_by_node
                and is_dict(self.type_by_node[target.value]))
            return True, True, True, isdict

        else:
            # unrecognised type. Add a warning and continue
            print("Warning: unrecognised variable type", file=sys.stderr)
            return True, False, True, False

    def unpack_lists(self, node) -> List[str]:
        """
        Is this a binary operator that we want to unpack, as its
        operands are lists? If so, return a list of all the
        operand variables that are lists, including those that are
        included indirectly, as operands of operands.
        """
        if self.unpacking:
            return None     # do not recurse

        elif not is_list(self.type_by_node[node]):
            return None     # not a list
        
        elif isinstance(node, ast.Name) and node.id in self.variables:
            # found a variable which is a list
            return [node.id]

        elif isinstance(node, ast.BinOp):
            left = self.unpack_lists(node.left)
            right = self.unpack_lists(node.right)
            result = []
            if left:
                result.extend(left)
            if right:
                result.extend(right)
            return result
        
        else:
            print("Warning: unhandled subnode of binary operator on lists", file=sys.stderr)
            return None

    def visit_FunctionDef(self, node):
        # Analyse the variables in this function to see which need
        # to be predeclared or marked as mutable
        analyser = VariableAnalyser(self.headers)
        analyser.visit(node)
        self.type_by_node = analyser.get_type_by_node()

        # function name. Always public, as Python has no
        # private functions.
        print(f"{self.pretty()}pub fn {node.name}(", end='')

        # start with a clean set of variables 
        # (do we need to worry about nested functions?)
        self.variables.clear()
        self.mutable_vars = analyser.get_mutable_vars()
        self.mutable_ref_vars = analyser.get_mutable_ref_vars()

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
        ref_type = "&mut " if node.arg in self.mutable_ref_vars else ""
        print(f"{self.next_separator}{mutable}{node.arg}: {ref_type}{typed}", end='')
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
        if node_path and len(node_path) == 1 and node_path[0] in STANDARD_FUNCTIONS:
            return STANDARD_FUNCTIONS[node_path[0]](self, node)

        # identify method calls, where the first item is a known variable
        is_method = len(node_path) > 1 and node_path[0] in self.variables

        # Function name, with namespacing if required. Note that if
        # any namespacing is required, we first need an initial
        # :: so we start from the global namespace.
        if len(node_path) > 1 and not is_method:
            print("::", end='')
        
        # may be some fancy footwork if this is a method on a standard type
        if is_method and node.func in self.type_by_node:
            func_type = self.type_by_node[node.func]
            method = (detemplatise(func_type), node_path[1])
            if method in STANDARD_METHODS:
                print(node_path[0], end='')
                return STANDARD_METHODS[method](self, node)

        separator = "." if is_method else "::"
        first = True
        for name in node_path:
            if not first:
                print(separator, end='')
            print(name, end='')
            first = False

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

    def visit_Tuple(self, node):
        print("(", end='')
        separator = ""
        for element in node.elts:
            print(separator, end='')
            self.visit(element)
            separator = ", "
        print(")", end='')

    def visit_List(self, node):

        # Always make a Vec rather than just a slice. We do not know
        # how it will be used.
        print("vec!", end='')
        self.do_visit_List(node)
        
    def do_visit_List(self, node):
        print("[", end='')
        
        # special-case empty or short lists for prettiness
        short = len(node.elts) < 3
        if not short:
            print()
            self.add_pretty(1)
            print(self.pretty(), end='')

        first = True
        for element in node.elts:
            if short and not first:
                print(", ", end='')
            # We want lists and sets of strings to be
            # List<String> rather than List<str>, which is
            # harder to handle the lifetimes of.
            self.visit_and_optionally_convert(element)
            first = False
            if not short:
                print(",")
                print(self.pretty(), end='')
        
        print("]", end='')
        if not short:
            self.add_pretty(-1)

    def visit_Set(self, node):
        # first construct a list, though without the vec! (a slice
        # is sufficient)
        self.do_visit_List(node)

        # then convert it to a HashSet
        print(".iter().cloned().collect::<HashSet<_>>()", end='')        

    def visit_Dict(self, node):
        print("[", end='')
        
        # special-case empty or short lists for prettiness
        short = len(node.values) < 3
        if not short:
            print()
            self.add_pretty(1)
            print(self.pretty(), end='')

        first = True
        for key, value in zip(node.keys, node.values):
            if short and not first:
                print(", ", end='')
            print("(", end='')
            self.visit_and_optionally_convert(key)
            print(", ", end='')
            self.visit_and_optionally_convert(value)
            print(")", end='')
            first = False
            if not short:
                print(",")
                print(self.pretty(), end='')
        
        print("].iter().cloned().collect::<HashMap<_, _>>()", end='')        

        if not short:
            self.add_pretty(-1)

    def visit_Subscript(self, node):
        """
        Subscript is used in Python for both lists and tuples. However, the
        subscript syntax in Rust is different for these two cases. We
        need to know which we are doing.
        """
        self.visit(node.value)
        typed = self.type_by_node[node.value]
        if typed and typed[0] == '(':
            print(".", end='')
            self.visit(node.slice)
        else:
            print("[", end='')
            self.visit(node.slice)
            print("]", end='')

    def visit_BinOp(self, node):
        # There needs to be special handling for Lists.
        # Python treats A o B as element-wise operator o
        # applied to every matching element in A and B.
        # Rust requires this to be explicit.
        #
        # e.g. python expression (a + b) * c turns into
        #
        # a.iter().zip(b.iter().zip(c.iter())).map(|(a,(b, c))|
        #     (a + b) * c
        #     ).collect::<Vec<_>>();
        #
        unpack = self.unpack_lists(node)
        if unpack:
            for i, var in enumerate(unpack):
                if i > 0:
                    print(".zip(", end='')
                print(f"{var}.iter()", end='')
            print(")" * i, end='')
            print(".map(|(", end='')
            n = len(unpack)
            for i, var in enumerate(unpack):
                if i == n - 1:
                    print(", ", end='')
                elif i > 0:
                    print(",(", end='')
                print(var, end='')
            print(")" * i, end='')
            print("|")
            self.add_pretty(1)
            print(self.pretty(), end='')
            self.unpacking = True

        # some binary operators such as '+' translate
        # into binary operators in Rust. However, pow needs
        # special handling.
        op = node.op.__class__.__name__
        if op == "Pow":
            self.visit_PowOp(node)
        else:
            self.parens_if_needed(op, lambda: self.do_visit_BinOp(node))

        # close the list special handling if needed
        if unpack:
            print()
            print(f"{self.pretty()}).collect::<Vec<_>>()", end='')
            self.add_pretty(-1)
            self.unpacking = False
    
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
        assert(op_len > 0)

        # in and is are special cases
        if isinstance(node.ops[0], ast.In):
            self.visit_In_Compare(node)
            return
        if isinstance(node.ops[0], ast.NotIn):
            print("!", end='')
            self.visit_In_Compare(node)
            return
        elif isinstance(node.ops[0], ast.Is):
            self.visit_Is_Compare(node, "==")
            return
        elif isinstance(node.ops[0], ast.IsNot):
            self.visit_Is_Compare(node, "!=")
            return

        if op_len > 1:
            print("(", end='')

        self.visit(node.left)
        for op, c, i in zip(node.ops, node.comparators, range(op_len)):
            op_name = op.__class__.__name__
            if op_name not in ALLOWED_COMPARISON_OPERATORS:
                print(f"Warning: {op_name} is not an operator", file=sys.stderr)
            self.visit(op)
            self.visit(c)
            if op_len > 1:
                if i != op_len - 1:
                    print(") && (", end='')
                    self.visit(c)
                else:
                    print(")", end='')

    def visit_Is_Compare(self, node, op: str):
        """
        Not part of the visitor pattern, but we special-case
        this from visit_Compare for an "is" operator.
        """
        assert(len(node.ops) == 1)
        assert(len(node.comparators) == 1)

        self.precedence = MAX_PRECEDENCE * 2    # "as" binds tightly in Rust
        self.visit(node.left)
        print(f" as *const _ {op} ", end='')
        self.visit(node.comparators[0])
        print(" as *const _", end='')

    def visit_In_Compare(self, node):
        """
        Not part of the visitor pattern, but we special-case
        this from visit_Compare for an "in" operator.
        """
        assert(len(node.ops) == 1)
        assert(len(node.comparators) == 1)

        self.visit(node.comparators[0])
        typed = extract_container(self.type_by_node[node.comparators[0]])
        use_position = False
        if typed == "HashSet<":
            print(".contains(", end='')
        elif typed == "HashMap<":
            print(".contains_key(", end='')
        else:
            # this method works for any container that supports 
            # iterators, but is linear in operation time.
            tmp = self.temp_variable()
            print_iter_if_needed(typed)
            print(".position(|", end='')
            add_reference_if_needed(self.type_by_node[node.left])
            print(f"{tmp}| {tmp} == ", end='')
            use_position = True

        self.precedence = 0
        self.visit(node.left)
        print(")", end='')
        if use_position:
            print(" != None", end='')

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

    def visit_ListComp(self, node):
        """
        A list comprehension in Rust can be achieved using the macros
        defined in the *cute* crate, but this ends up producing non-
        standard Rust source. We stay more mainstream and render
        comprehensions as follows:

        l = [foo(x) for x in range(100) if bar(x)]

        let l = (0..100).filter(|x| bar(x)).map(|x| foo(x)).collect::<Vec<_>>();

        We leave the more unusual case of more than one generator as
        an exercise...
        """
        self.do_visit_Comprehension(node)
        print(".collect::<Vec<_>>()", end='')

    def visit_SetComp(self, node):
        self.do_visit_Comprehension(node)
        print(".collect::<HashSet<_>>()", end='')

    def visit_DictComp(self, node):
        first = True
        for generator in node.generators:
            if not first:
                print(", ", end='')
            self.visit(generator)
            first = False

        # shortcut if key and value are just a variable name, otherwise need a map
        if not isinstance(node.key, ast.Name) or not isinstance(node.value, ast.Name):
            print(f".map(|{self.target}| (", end='')
            self.visit(node.key)
            print(", ", end='')
            self.visit(node.value)
            print("))", end='')
        print(".collect::<HashMap<_, _>>()", end='')

    def do_visit_Comprehension(self, node):
        """
        Helper function for comprehensions. Does all the work apart 
        from the final collection into the desired type.
        """
        if len(node.generators) != 1:
            print("Warning: comprehensions with more than one generator not supported")

        # writes (0..100).filter(|x| bar(x))
        for generator in node.generators:
            self.visit(generator)

        # shortcut if elt is just a variable name, otherwise need a map
        if not isinstance(node.elt, ast.Name):
            print(f".map(|{self.target}| ", end='')
            self.visit(node.elt)
            print(")", end='')

    def visit_comprehension(self, node):
        """
        A comprehension in Rust is rendered as a generator as
        follows:

            l = [foo(x) for x in range(100) if bar(x)]
        
        the generator is

            for x in range(100) if bar(x)

        in Rust, this is

            (0..100).filter(|x| bar(x))
        """

        # first find out the target. This is either a variable
        # (Name) or a Tuple.
        self.target = target_as_string(node.target)

        # iterator e.g. (0..100)
        self.precedence = MAX_PRECEDENCE * 2
        self.visit(node.iter)    # (0..100)

        # if statements e.g. .filter(|x| bar(x))
        for i in node.ifs:
            print(f".filter(|{self.target} ", end='')
            self.visit(i)
            print(")", end='')

    def visit_Assert(self, node):
        print(f"{self.pretty()}assert!(", end='')
        self.visit(node.test)
        if node.msg:
            print(", ", end='')
            self.visit(node.msg)
        print(");")
    
    def visit_Delete(self, node):
        """
        In Python you can delete any variable in whole or part.
        However, it only really makes sense when deleting an
        item from a container such as a dictionary.

            del foo("bar") foo("BAR")

        translates to 

            foo.remove("bar");
            foo.remove("BAR");
        """
        for t in node.targets:
            if isinstance(t, ast.Subscript):
                print(self.pretty(), end='')
                self.visit(t.value)
                print(".remove(", end='')
                self.visit(t.slice)
                print(");")
            else:
                print("Warning: del only implemented for collections", sys.stderr)

    def visit_Assign(self, node):
        """
        Variable assignment statement, such as x = y = 42

        Note that Rust does not handle multiple assignments on one
        line, so we write a line for each one.
        """
        first = True
        for target in node.targets:
            print(f"{self.pretty()}", end='')

            # treatment depends on whether it is the first time we
            # have seen this variable. (Do not use shadowing.)
            mutable, declared, assignable, isdict = self.sex_variable(target)
            tmp_var_name = None

            if isdict:
                self.visit(target.value)
                print(".insert(", end='')
                self.visit_and_optionally_convert(target.slice)
                print(", ", end='')

            elif not declared:
                print("let ", end='')
                if mutable and assignable:
                    print("mut ", end='')

            elif not assignable:
                # May be a tuple. This is tricky in Rust. Where Python supports
                # a, b = foo(), Python only supports this inside a let declaration:
                # let (a, b) = foo(). The assignable flag tells us this. If
                # necessary use a temp variable.
                tmp_var_name = self.temp_variable()

            if tmp_var_name:
                print(f"let {tmp_var_name} = ", end='')
            elif not isdict:
                self.visit(target)      # assign directly to what we want
                print(" = ", end='')

            if first:
                self.precedence = 0     # don't need params around value
                self.visit_and_optionally_convert(node.value)
                first_target = target
                first = False
            else:
                # only evaluate expression once
                self.visit(first_target)

            if isdict:
                print(")", end='')
            print(";")

            # now we may need to assign what we originally wanted to
            if tmp_var_name:
                self.assign_tuple(target, tmp_var_name)

    def assign_tuple(self, node, tmp_var_name: str):
        """
        As Rust does not allow direct assignment to an unpacked
        tuple, e.g. a, b = foo(), we unpack this into multiple
        lines:

        let tmp = foo()
        a = tmp.1
        b = tmp.2
        """
        assert(isinstance(node, ast.Tuple))
        for i, element in enumerate(node.elts):
            print(self.pretty(), end='')
            self.visit(element)
            print(f" = {tmp_var_name}.{i};")

    def visit_AnnAssign(self, node):
        """
        Hinted variable assignment statement, such as x: int = 42

        We do not yet handle non-simple assignments such as
        (x): int = 42
        """
        # treatment depends on whether it is the first time we
        # have seen this variable. (Do not use shadowing.)
        mutable, declared, _, _ = self.sex_variable(node.target)
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
    baseline_filename = f"src/{filename}.rs"
    
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

    dependencies = DependencyAnalyser(function_finder.headers)
    dependencies.visit(tree)
    dependencies.write_preamble()

    RustGenerator(function_finder.headers).visit(tree)
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
    test_compiler("lists")
    test_compiler("sets")
    test_compiler("dictionaries")

