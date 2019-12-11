"""
Module supporting analysis of variable declaration and usage.
"""

import ast
import sys
from typing import Dict, Set, List, Tuple, get_type_hints
import filecmp
import os

# Mapping from pair of Rust types (e.g. a binary op) to Rust type
TYPE_COERCIONS = {
    ("bool", "i64"): "i64",
    ("i64", "bool"): "i64",
    ("bool", "f64"): "f64",
    ("f64", "bool"): "f64",
    ("i64", "f64"): "f64",
    ("f64", "i64"): "f64",
}

UNKNOWN_TYPE = "Unknown"

# Mapping from Rust type to Rust default initialiser
DEFAULT_VALUES = {
    "bool": "false",
    "i64": "0",
    "f64": "0.0",
    "String": 'String::new()',
    "&str": '""'
}

# Mapping from Python type to Rust equivalent (arg type)
TYPE_MAPPING = {
    "bool": "bool",
    "int": "i64",
    "long": "i64",
    "float": "f64",
    "str": "&str",
}

# Mapping from Python function name to Rust return type
STANDARD_FUNCTION_RETURNS = {
    "print": "()",
    "range": "std::ops::Range"
}

CONTAINER_CONVERSIONS = {
    "&str": ".to_string()"
}

def type_from_annotation(annotation: str, arg: str, container: bool) -> str:
    if annotation is None:
        print("missing type annotation for argument '{arg}'", file=sys.stderr)
        return 'None'
    id = annotation.id
    if id in TYPE_MAPPING:
        arg_type = TYPE_MAPPING[id]
        return container_type(arg_type) if container else arg_type
    else:
        print("unrecognised type annotation for argument '{arg}': '{id}'", file=sys.stderr)
        return annotation

def container_type(arg_type: str) -> str:
    """
    Given an arg type (the sort of type that is passed as a
    function arg) return a container type (the sort of type that
    is returned from a function, or used as a variable).
    """
    if arg_type == "&str":
        return "String"
    else:
        return arg_type

def container_type_needed(node, types: Dict[object, str]) -> str:
    """
    If the given node's type requires coercion to make
    it useable as a container type, return the string to
    do the conversion. (E.g. "&str" requires ".to_string())
    """
    if node in types:
        typed = types[node]
        if typed in CONTAINER_CONVERSIONS:
            return CONTAINER_CONVERSIONS[typed]
    return None
    
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
        self.type_by_node: Dict[object, str] = {}
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

    def get_type_by_node(self) -> Dict[object, str]:
        """
        After running visit, this returns a map from AST node
        to type string
        """
        return self.type_by_node

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

    def write_access(self, var: str, typed: str, node):
        if var not in self.vars:
            if typed == UNKNOWN_TYPE:
                raise Exception("Cannot declare variable of mixed type")
            self.vars[var] = VariableInfo(False, typed)
        else:
            # A second write to a variable means it must be mutable.
            # Ignore the type in this case, as the Rust compiler will
            # flag any incompatibilities.
            self.vars[var].mutable = True
        self.type_by_node[node] = typed

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
    
    def set_type(self, typed: str, node):
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

        self.type_by_node[node] = self.current_type

    def set_type_container(self, node):
        """
        Ensure the current type and that set for the current node
        is a container type, suitable for return or assignment.
        """
        self.current_type = container_type(self.current_type)
        self.type_by_node[node] = self.current_type

    def clear_type(self):
        self.current_type = ""

    def generic_visit(self, node):
        """
        Override generic visit to first visit as per standard visitor,
        then record the type in the type dictionary
        """
        super().generic_visit(node)
        self.type_by_node[node] = self.current_type

    def visit_arg(self, node):
        typed = type_from_annotation(node.annotation, node.arg, False)
        if node.arg in self.vars:
            raise Exception(f"Repeated argument: {node.arg}")
        self.vars[node.arg] = VariableInfo(True, typed)
        self.type_by_node[node] = typed

    def visit_Name(self, node):
        typed = self.read_access(node.id)
        self.set_type(typed, node)

    def visit_Call(self, node):
        """
        Try to find the return type of the function we are calling.
        Also assign the right types to the args.
        """
        # recurse through the arguments
        prev = self.current_type
        for a in node.args:
            self.visit(a)
        self.current_type = prev

        # a few functions are well-known (and in any case, they
        # do not behave properly with the below code)
        func_name = node.func.id
        if func_name in STANDARD_FUNCTION_RETURNS:
            self.set_type(STANDARD_FUNCTION_RETURNS[func_name], node)
            return

        # try to find the type of the function
        namespace = __import__(__name__)
        try:
            func = getattr(namespace, func_name)
            types = get_type_hints(func)
            if "return" in types:
                typed = type_from_annotation(types["return"], func_name, True)
                self.set_type(typed, node)

        except AttributeError:
            pass

    def visit_Return(self, node):
        """
        We always return a contained type
        """
        self.generic_visit(node)
        self.set_type_container(node)

    def visit_NameConstant(self, node):
        # TODO what types can NameConstants be?
        self.set_type("bool", node)

    def visit_Str(self, node):
        """
        The type of a hardcoded string in Rust is &str, which
        can be turned into a String type by either my_str.to_string()
        or String::from(my_str).
        """
        self.set_type("&str", node)

    def visit_Num(self, node):
        python_type = type(node.n).__name__
        if python_type == 'int' or python_type == 'long':
            self.set_type("i64", node)
        elif python_type == 'float':
            self.set_type("f64", node)
        else:
            raise Exception(f"Unsupported numeric type: {python_type}")

    def visit_BinOp(self, node):
        """
        A binary operator acting on a reference type such as a &str
        must be coerced to a container type such as a String
        """
        self.visit(node.left)
        self.visit(node.op)
        self.visit(node.right)
        self.set_type_container(node)

    def visit_UnaryOp(self, node):
        """
        The not operator acting on any type returns a bool.
        """
        self.visit(node.op)
        self.visit(node.operand)
        op = node.op.__class__.__name__
        if op == "Not":
            self.clear_type()
            self.set_type("bool", node)
        else:
            self.type_by_node[node] = self.current_type

    def visit_BoolOp(self, node):
        """
        Any boolean operator (and/or) returns a bool, regardless
        of its operands
        """
        self.visit(node.op)
        for v in node.values:
            self.visit(v)
        self.clear_type()
        self.set_type("bool", node)

    def visit_Compare(self, node):
        # the result of a comparison is always a bool, regardless of
        # the contained values
        self.generic_visit(node)
        self.clear_type()
        self.set_type("bool", node)

    def visit_IfExp(self, node):
        # ignore the types of anything in the if condition from the point
        # of view of the returned type. However, we know this if condition
        # must be a bool.
        prev = self.current_type
        self.visit(node.test)
        self.type_by_node[node.test] = "bool"
        self.current_type = prev
        self.visit(node.body)
        self.visit(node.orelse)
        self.type_by_node[node] = self.current_type

    def visit_If(self, node):
        self.visit(node.test)
        self.type_by_node[node.test] = "bool"
        prev = self.enter_scope()
        for line in node.body:
            self.clear_type()
            self.visit(line)
        self.exit_scope(prev)
        prev = self.enter_scope()
        for line in node.orelse:
            self.clear_type()
            self.visit(line)
        self.exit_scope(prev)

    def visit_While(self, node):
        self.visit(node.test)
        self.type_by_node[node.test] = "bool"
        prev = self.enter_scope()
        for line in node.body:
            self.clear_type()
            self.visit(line)
        self.exit_scope(prev)
    
    def visit_For(self, node):
        self.visit(node.target)
        self.visit(node.iter)
        prev = self.enter_scope()
        for line in node.body:
            self.clear_type()
            self.visit(line)
        self.exit_scope(prev)
    
    def visit_Assign(self, node):
        self.clear_type()
        self.visit(node.value)
        for target in node.targets:
            self.write_access(target.id, container_type(self.current_type), target)

    def visit_AnnAssign(self, node):
        self.clear_type()
        self.visit(node.value)
        typed = type_from_annotation(node.annotation, node.target, True)
        self.write_access(node.target.id, typed, node.target)

    def visit_AugAssign(self, node):
        # x += foo is the same as x = x + foo
        typed = self.read_access(node.target)
        self.visit(node.value)
        self.write_access(node.target.id, typed, node.target)

class TestTreePrinter(ast.NodeVisitor):
    def __init__(self, types):
        self.types = types
        
    def generic_visit(self, node):
        typed = self.types[node] if node in self.types else "<unknown>"
        print(f"    {node.__class__.__name__}: type={typed}")
        super().generic_visit(node)

class TestFunctionFinder(ast.NodeVisitor):
    """
    Simply used for testing. Invoke VariableAnalyser
    on each function we see
    """
    def visit_FunctionDef(self, node):
        print(f"Function {node.name}:")
        analyser = VariableAnalyser()
        analyser.visit(node)
        type_by_node = analyser.get_type_by_node()

        tree_printer = TestTreePrinter(type_by_node)
        for expr in node.body:
            tree_printer.visit(expr)
        print()

def test_analyser(filename):
    input_filename = f"tests/{filename}.py"
    output_filename = f"temp/{filename}_var_analysis.txt"
    baseline_filename = f"baseline/{filename}_var_analysis.txt"

    input_file = open(input_filename, 'r')
    source = input_file.read()
    input_file.close()

    output_file = open(output_filename, 'w')
    old_stdout = sys.stdout
    sys.stdout = output_file
    tree = ast.parse(source, filename, 'exec')
    TestFunctionFinder().visit(tree)
    output_file.close()
    sys.stdout = old_stdout

    ok = filecmp.cmp(baseline_filename, output_filename, shallow=False)
    if ok:
        print(f"test {filename} succeeded")
        os.remove(output_filename)
    else:
        print(f"test {filename} failed. Output file {output_filename} left in place.")

if __name__ == "__main__":
    test_analyser("hello_world")
    test_analyser("add_mult")
    test_analyser("flow_of_control")
    test_analyser("variables")
