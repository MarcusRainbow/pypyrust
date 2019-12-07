"""
Module supporting analysis of variable declaration and usage.
"""

import ast
import sys
from typing import Dict, Set, List, Tuple

TYPE_COERCIONS = {
    ("bool", "i64"): "i64",
    ("i64", "bool"): "i64",
    ("bool", "f64"): "f64",
    ("f64", "bool"): "f64",
    ("i64", "f64"): "f64",
    ("f64", "i64"): "f64",
}

UNKNOWN_TYPE = "Unknown"

DEFAULT_VALUES = {
    "bool": "false",
    "i64": "0",
    "f64": "0.0",
    "str": '""',
}

def type_from_annotation(annotation: str, arg: str) -> str:
    if annotation is None:
        print("missing type annotation for argument '{arg}'", file=sys.stderr)
        return 'None'
    id = annotation.id
    if id == 'int':
        return 'i64'
    elif id == 'bool':
        return 'bool'
    elif id == 'str':
        return 'str'
    elif id == 'num':
        return 'f64'
    else:
        print("unrecognised type annotation for argument '{arg}': '{annotation}'", file=sys.stderr)
        return annotation

class VariableInfo:
    """
    Class that represents the declaration and usage of a variable.
    """
    def __init__(self, is_arg: bool, typed: str):
        self.is_arg = is_arg
        self.mutable = False
        self.typed = typed

class VariableAnalyser(ast.NodeVisitor):
    """
    Visitor of the Python AST which analyses variable declaration
    and usage. Results are retained internally.
    """

    def __init__(self):
        self.vars: Dict[str, VariableInfo] = {}
        self.out_of_scope: Dict[str, VariableInfo] = {}
        self.need_predeclaring: Dict[str, VariableInfo] = {}
        self.current_type = ""

    def get_predeclared_vars(self) -> List[Tuple[str, str, str]]:
        """ 
        After running visit, we can return a list of variables,
        types, and initial values that need predeclaring. All must be
        declared mutable.
        """
        return [(v, i.typed, DEFAULT_VALUES[i.typed]) 
            for (v, i) in self.need_predeclaring.items()]

    def get_mutable_vars(self) -> Set[str]:
        """
        After running visit, this can return a set of variables
        that need to be marked as mutable.
        """
        return {v for (v, i) in self.vars.items() if i.mutable}

    def read_access(self, var: str) -> str:
        """
        Note a variable used for reading. If it was written to
        in this scope, that is fine. If it was written to
        in some contained scope, that is something Python
        accepts but not Rust, so we need to predeclare it.
        If it was not written to at all, raise an error.

        Returns the type of the variable
        """
        if var in self.vars:
            return self.vars[var].typed
        elif var in self.out_of_scope:
            info = self.out_of_scope[var]
            self.need_predeclaring[var] = info
            return info.typed

        # The else case here picks up all sorts of things we do not
        # naturally thing of as variables, such as the names of
        # functions. For now just return "".
        return ""

    def write_access(self, var: str, typed: str):
        if var not in self.vars:
            if typed == UNKNOWN_TYPE:
                raise Exception("Cannot declare variable of mixed type")
            self.vars[var] = VariableInfo(False, typed)
        else:
            # A second write to a variable means it must be mutable.
            # Ignore the type in this case, as the Rust compiler will
            # flag any incompatibilities.
            self.vars[var].mutable = True

    def enter_scope(self) -> Dict[str, VariableInfo]:
        return self.vars.copy()

    def exit_scope(self, prev: Dict[str, VariableInfo]):
        # throw away any new variables from this scope,
        # but remember about them, as Python would allow
        # them to be used later on.
        to_delete = []
        for key, value in self.vars.items():
            if key not in prev:
                self.out_of_scope[key] = value
                to_delete.append(key)
        
        for key in to_delete:
            del self.vars[key]
    
    def set_type(self, typed: str):
        """
        Merges the given type into whatever type we have using
        standard coercion rules. E.g. int + float -> float
        """
        if not typed:
            pass    # ignore unknown types
        elif not self.current_type:
            self.current_type = typed
        elif self.current_type == typed:
            pass    # already right
        elif (self.current_type, typed) in TYPE_COERCIONS:
            self.current_type = TYPE_COERCIONS[(self.current_type, typed)]
        else:
            self.current_type = UNKNOWN_TYPE

    def clear_type(self):
        self.current_type = ""

    def visit_arg(self, node):
        typed = type_from_annotation(node.annotation, node.arg)
        if node.arg in self.vars:
            raise Exception(f"Repeated argument: {node.arg}")
        self.vars[node.arg] = VariableInfo(True, typed)

    def visit_Name(self, node):
        typed = self.read_access(node.id)
        self.set_type(typed)

    def visit_Call(self, node):
        # TODO need to find the type of the return value of the call
        # no need to visit the call, which will just pull in irrelevant types
        pass

    def visit_NameConstant(self, node):
        # TODO what types can NameConstants be?
        self.set_type("bool")

    def visit_Str(self, node):
        self.set_type("str")

    def visit_Num(self, node):
        python_type = type(node.n).__name__
        if python_type == 'int' or python_type == 'long':
            self.set_type("i64")
        elif python_type == 'float':
            self.set_type("f64")
        else:
            raise Exception(f"Unsupported numeric type: {python_type}")

    def visit_Compare(self, node):
        # the result of a comparison is always a bool, regardless of
        # the contained values
        prev = self.current_type
        self.generic_visit(node)
        self.current_type = prev
        self.set_type("bool")

    def visit_IfExp(self, node):
        # ignore the types of anything in the if condition
        prev = self.current_type
        self.visit(node.test)
        self.current_type = prev
        self.visit(node.body)
        self.visit(node.orelse)

    def visit_If(self, node):
        self.visit(node.test)
        prev = self.enter_scope()
        for line in node.body:
            self.visit(line)
        self.exit_scope(prev)
        prev = self.enter_scope()
        for line in node.orelse:
            self.visit(line)
        self.exit_scope(prev)

    def visit_While(self, node):
        self.visit(node.test)
        prev = self.enter_scope()
        for line in node.body:
            self.visit(line)
        self.exit_scope(prev)
    
    def visit_For(self, node):
        self.visit(node.target)
        self.visit(node.iter)
        prev = self.enter_scope()
        for line in node.body:
            self.visit(line)
        self.exit_scope(prev)
    
    def visit_Assign(self, node):
        self.clear_type()
        self.visit(node.value)
        for target in node.targets:
            self.write_access(target.id, self.current_type)

    def visit_AnnAssign(self, node):
        self.clear_type()
        self.visit(node.value)
        typed = type_from_annotation(node.annotation, node.target)
        self.write_access(node.target.id, typed)

    def visit_AugAssign(self, node):
        # x += foo is the same as x = x + foo
        typed = self.read_access(node.target)
        self.clear_type()
        self.visit(node.value)
        self.write_access(node.target.id, typed)

def test_var():
    pass

if __name__ == "__main__":
    test_var()
