"""
Module supporting analysis of variable declaration and usage.
"""

import ast
import sys
from typing import Dict, Set, List, Tuple, get_type_hints
import filecmp
import os
from importlib import import_module, invalidate_caches
from library_functions import method_return_type, STANDARD_FUNCTION_RETURNS
from var_utils import type_from_annotation, merge_types, container_type, \
    strip_container, UNKNOWN_TYPE
from headers import FunctionHeader, FunctionHeaderFinder

# Mapping from Rust type to Rust default initialiser
DEFAULT_VALUES = {
    "bool": "false",
    "i64": "0",
    "f64": "0.0",
    "String": 'String::new()',
    "&str": '""'
}

def get_node_path(node) -> List[str]:
    """
    Returns the address of a node, starting from the global namespace
    """
    if isinstance(node, ast.Name):
        return [node.id]    # already in the global namespace
    elif isinstance(node, ast.Attribute):
        # recurse, adding nodes until we get to a global name
        path = get_node_path(node.value)
        path.append(node.attr)
        return path
    else:
        raise Exception("Cannot find path to node")

IMPORTED_MODULES = {}
def load_and_import_module(name: str) -> object:
    if name in IMPORTED_MODULES:
        return IMPORTED_MODULES[name]
    
    module = import_module(name)
    invalidate_caches()
    IMPORTED_MODULES[name] = module
    return module

class VariableInfo:
    """
    Class that represents the declaration and usage of a variable.
    """
    def __init__(self, is_arg: bool, typed: str):
        self.is_arg = is_arg
        self.mutable = False
        self.mutable_ref = False
        self.typed = typed
class VariableAnalyser(ast.NodeVisitor):
    """
    Visitor of the Python AST which analyses variable declaration
    and usage. Results are retained internally.
    """

    def __init__(self, headers: Dict[str, FunctionHeader]):
        """
        The return types are a dictionary of local function name
        to return type.
        """
        self.headers = headers
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

    def get_mutable_ref_vars(self) -> Set[str]:
        """
        After running visit, this can return a set of variables
        that need to be marked as mutable reference.
        """
        return {v for (v, i) in self.vars.items() if i.mutable_ref}

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
        Sets the given type into the annotations and the
        current type.
        """
        self.current_type = typed
        self.type_by_node[node] = self.current_type

    def merge_type(self, typed: str, node):
        """
        Merges the given type into whatever type we have using
        standard coercion rules. E.g. int + float -> float
        """
        self.set_type(merge_types(self.current_type, typed), node)

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
        arg_types = []
        for a in node.args:
            self.visit(a)
            arg_types.append(self.current_type)
        self.current_type = prev

        # a few functions are well-known (and in any case, they
        # do not behave properly with the below code)
        func_path = get_node_path(node.func)
        if func_path and len(func_path) == 1 and func_path[0] in STANDARD_FUNCTION_RETURNS:
            self.set_type(STANDARD_FUNCTION_RETURNS[func_path[0]](arg_types), node)
            return

        # Assume function names with no module are defined locally
        if len(func_path) == 1:
            if func_path[0] not in self.headers:
                print(f"Warning: cannot find function return for: {func_path[0]}",
                    file = sys.stderr)
            else:
                self.set_type(self.headers[func_path[0]].returns, node)

        # If the first part of the path is a known variable, then this is
        # a method call on that variable. Ignore for now, apart from setting
        # the type of the variable
        if func_path[0] in self.vars:
            self.visit(node.func)
            typed = method_return_type(self.current_type, func_path[1])
            self.set_type(typed, node)

            # for now, we assume that any method invoked on an object can
            # mutate that object
            self.vars[func_path[0]].mutable_ref = True
            return

        # We currently only handle module.func_name
        if len(func_path) != 2:
            return

        # Locate the function. In order to do this, we actually load
        # the module of interest into our own process space. Maybe
        # consider making this optional, as it is a bit of a
        # sledgehammer.
        module_name = func_path[0]
        func_name = func_path[1]
        namespace = load_and_import_module(module_name)
        func = getattr(namespace, func_name)

        # try to find the type of the function
        types = get_type_hints(func)
        if "return" in types:
            typed = type_from_annotation(types["return"],func_name, True)
            self.set_type(typed, node)

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

    def visit_Tuple(self, node):
        types = []
        for element in node.elts:
            self.visit(element)
            types.append(self.current_type)
        
        type_string = f"({', '.join(types)})"
        self.set_type(type_string, node)

    def visit_List(self, node):
        element_type = ""
        for element in node.elts:
            self.visit(element)
            element_type = merge_types(element_type, self.current_type)
        self.set_type(f"&[{element_type}]", node)

    def visit_Set(self, node):
        element_type = ""
        for element in node.elts:
            self.visit(element)
            element_type = merge_types(element_type, self.current_type)
        self.set_type(f"HashSet<{element_type}>", node)

    def visit_Dict(self, node):
        key_type = ""
        value_type = ""

        for key in node.keys:
            self.visit(key)
            key_type = merge_types(key_type, self.current_type)
        for value in node.values:
            self.visit(value)
            value_type = merge_types(value_type, self.current_type)

        self.set_type(f"HashMap<{key_type}, {value_type}>", node)

    def visit_Subscript(self, node):
        """
        Current type is the type of the container. We want the type
        of the element. For now, we assume that if the subscript is a
        constant, we can use that element of the type. Otherwise hope
        the array is consistently typed, and just use the first.
        """

        self.visit(node.slice)      # the integer type of the index
        self.visit(node.value)      # the name of the variable

        types = strip_container(self.current_type).split(", ")
        try:
            index = ast.literal_eval(node.slice)
        except:
            index = 0   # if the index is not constant, just use the first

        self.set_type(f"&{types[index]}", node)

    def visit_BinOp(self, node):
        """
        A binary operator acting on a reference type such as a &str
        must be coerced to a container type such as a String
        """
        self.visit(node.left)
        left = self.current_type
        self.visit(node.op)
        self.visit(node.right)
        self.merge_type(left, node)
        self.set_type_container(node)

    def visit_UnaryOp(self, node):
        """
        The not operator acting on any type returns a bool.
        """
        self.visit(node.op)
        self.visit(node.operand)
        op = node.op.__class__.__name__
        if op == "Not":
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
        self.set_type("bool", node)

    def visit_Compare(self, node):
        # the result of a comparison is always a bool, regardless of
        # the contained values
        self.visit(node.left)
        for comparator in node.comparators:
            self.visit(comparator)
        self.set_type("bool", node)

    def visit_IfExp(self, node):
        # ignore the types of anything in the if condition from the point
        # of view of the returned type. However, we know this if condition
        # must be a bool.
        self.visit(node.test)
        self.type_by_node[node.test] = "bool"
        self.visit(node.body)
        self.visit(node.orelse)
        self.type_by_node[node] = self.current_type

    def visit_If(self, node):
        self.visit(node.test)
        self.type_by_node[node.test] = "bool"
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
        self.type_by_node[node.test] = "bool"
        prev = self.enter_scope()
        for line in node.body:
            self.visit(line)
        self.exit_scope(prev)
    
    def visit_For(self, node):
        # the iterator should return some kind of container or iterator
        # type over the type of the target, a kind of repeated assignment
        self.visit(node.iter)
        typed = strip_container(self.current_type)
        self.handle_assignment(node.target, typed)
        prev = self.enter_scope()
        for line in node.body:
            self.visit(line)
        self.exit_scope(prev)
    
    def visit_ListComp(self, node):
        for generator in node.generators:
            self.visit(generator)
        self.visit(node.elt)
        self.set_type(f"&[{self.current_type}]", node)

    def visit_SetComp(self, node):
        for generator in node.generators:
            self.visit(generator)
        self.visit(node.elt)
        self.set_type(f"HashSet<{self.current_type}>", node)

    def visit_DictComp(self, node):
        for generator in node.generators:
            self.visit(generator)
        self.visit(node.key)
        key = self.current_type
        self.visit(node.value)
        value = self.current_type
        self.set_type(f"HashMap<{key}, {value}>", node)

    def visit_comprehension(self, node):
        # target, iter, ifs
        self.visit(node.iter)
        typed = strip_container(self.current_type)
        self.handle_assignment(node.target, typed)
        
        # if there are any if statements, enter into them
        # to set their internal types, but the overall
        # type returned by the comprehension is unaffected
        prev_type = self.current_type
        for i in node.ifs:
            self.visit(i)
        self.current_type = prev_type

    def visit_Assign(self, node):
        self.visit(node.value)
        for target in node.targets:
            self.handle_assignment(target, self.current_type)
        
    def handle_assignment(self, target, typed: str):

        # May just be a single variable to assign
        if isinstance(target, ast.Name):
            self.write_access(target.id, container_type(typed), target)

        # May be a tuple. e.g. a, b = foo()
        elif isinstance(target, ast.Tuple):
            if typed[0] != '(' or typed[-1] != ')':
                print("Warning: cannot assign tuple from non-tuple", file=sys.stderr)
                return
            
            subtypes = strip_container(typed).split(", ")
            for e, subtype in zip(target.elts, subtypes):
                self.handle_assignment(e, subtype)
        
        # May be a Subscript. E.g. foo[0] = bar. Ensure the variable
        # is mutable reference
        elif isinstance(target, ast.Subscript):
            container = target.value.id
            self.vars[container].mutable_ref = True
            self.visit(target)
        
        # Anything else, just make sure we visit it
        else:
            self.visit(target)

    def visit_AnnAssign(self, node):
        self.visit(node.value)
        typed = type_from_annotation(node.annotation, node.target, True)
        self.handle_assignment(node.target, typed)

    def visit_AugAssign(self, node):
        # x += foo is the same as x = x + foo

        # TODO node.target may be an attribute (e.g. self.foo)
        typed = self.read_access(node.target.id)
        self.set_type(typed, node.target)
        self.visit(node.value)
        self.handle_assignment(node.target, typed)

class TestTreePrinter(ast.NodeVisitor):
    def __init__(self, types):
        self.types = types
        
    def generic_visit(self, node):
        typed = self.types[node] if node in self.types else "<unknown>"
        print(f"    {node.__class__.__name__}: type={typed}")
        super().generic_visit(node)

    def visit_Name(self, node):
        typed = self.types[node] if node in self.types else "<unknown>"
        print(f"    Name({node.id}): type={typed}")

class TestFunctionFinder(ast.NodeVisitor):
    """
    Simply used for testing. Invoke VariableAnalyser
    on each function we see
    """
    def __init__(self, return_types):
        self.return_types = return_types

    def visit_FunctionDef(self, node):
        print(f"Function {node.name}:")
        analyser = VariableAnalyser(self.return_types)
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
    TestFunctionFinder(function_finder.headers).visit(tree)

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
    test_analyser("hello_world")
    test_analyser("add_mult")
    test_analyser("flow_of_control")
    test_analyser("variables")
    test_analyser("function_calls")
    test_analyser("tuples")
    test_analyser("lists")
    test_analyser("sets")
    test_analyser("dictionaries")
    # test_analyser("classes")
