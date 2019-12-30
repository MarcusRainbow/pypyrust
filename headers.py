import ast
import sys
import os
import filecmp
from typing import Dict, List
from var_utils import type_from_annotation, numeric_type

class FunctionHeader:
    def __init__(self, returns: str, args: [(str, str)]):
        self.returns = returns
        self.args = args

class ClassHeader:
    def __init__(
            self, 
            bases: List[str], 
            methods: Dict[str, FunctionHeader],
            instance_attributes: Dict[(str, str)]):
        self.bases = bases
        self.instance_attributes = instance_attributes
        self.methods = methods

class InstanceAttributeFinder(ast.NodeVisitor):
    """
    Given an AST representing part of the __init__ method
    of a class, find all the attribute definitions.
    """
    def __init__(self, args: Dict[str, str]):
        self.args = args
        self.attributes: Dict[str, str] = {}    # name, type
    
    def visit_Assign(self, node):
        for target in node.targets:
            if (isinstance(target, ast.Attribute) and
                isinstance(target.value, ast.Name) and
                target.value.id == "self"):
                # got a member variable definition
                name = target.attr

                # Consider using the full force of variable analyser here
                # (though there are issues of circular dependencies). For
                # now we just handle two cases -- direct access to arguments
                # and constants.
                if isinstance(node.value, ast.Name) and node.value.id in self.args:
                    self.attributes[name] = self.args[node.value.id]
                elif isinstance(node.value, ast.NameConstant):
                    self.attributes[name] = "bool"
                elif isinstance(node.value, ast.Num):
                    self.attributes[name] = numeric_type(node.value)
                elif isinstance(node.value, ast.Str):
                    self.attributes[name] = "String"
                  
                else:
                    print(f"Warning: cannot deduce type of attribute {name}", file=sys.stderr)
                    self.attributes[name] = "unknown"
        
    def visit_AnnAssign(self, node):
        if (isinstance(node.target, ast.Attribute) and
            isinstance(node.target.value, ast.Name) and
            node.target.value.id == "self"):
            # got a member variable definition
            name = node.target.attr
            typed = type_from_annotation(node.annotation, node.target, True)
            self.attributes[name] = typed

class ClassHeaderFinder(ast.NodeVisitor):
    """
    Given an AST representing a class, find all the method
    definitions and record the return and arg types.
    """

    def __init__(self):
        self.methods : Dict[str, FunctionHeader] = {}

    def visit_FunctionDef(self, node):
        name = node.name
        returns = type_from_annotation(node.returns, f"{name} return", True)
        args = []
        for arg in node.args.args:
            argname = arg.arg
            typed = type_from_annotation(arg.annotation, f"{name}: {argname}", False)
            args.append((argname, typed))
        
        self.methods[name] = FunctionHeader(returns, args)

        # If this is the __init__ method, any assignments to self.<something>
        # are effectively variable declarations.
        if name == "__init__":
            finder = InstanceAttributeFinder(dict(args))
            for line in node.body:
                finder.visit(line)
            
            self.instance_attributes = finder.attributes

class FunctionHeaderFinder(ast.NodeVisitor):
    """
    Given an AST representing a module, find all the function
    definitions and record the return types.
    """

    def __init__(self):
        self.headers : Dict[str, FunctionHeader] = {}
        self.class_headers : Dict[str, ClassHeader] = {}

    def visit_FunctionDef(self, node):
        name = node.name
        returns = type_from_annotation(node.returns, f"{name} return", True)
        args = []
        for arg in node.args.args:
            argname = arg.arg
            typed = type_from_annotation(arg.annotation, f"{name}: {argname}", False)
            args.append((argname, typed))
        
        self.headers[name] = FunctionHeader(returns, args)

    def visit_ClassDef(self, node):
        # visit the whole of the class definition via a ClassHeaderFinder
        method_finder = ClassHeaderFinder()
        for line in node.body:
            method_finder.visit(line)

        # Use this to construct the class headers
        self.class_headers[node.name] = ClassHeader(node.bases, 
            method_finder.methods, method_finder.instance_attributes)

def test_headers(filename):
    input_filename = f"tests/{filename}.py"
    output_filename = f"temp/{filename}_headers.txt"
    baseline_filename = f"baseline/{filename}_headers.txt"

    input_file = open(input_filename, 'r')
    source = input_file.read()
    input_file.close()

    output_file = open(output_filename, 'w')
    old_stdout = sys.stdout
    sys.stdout = output_file
    tree = ast.parse(source, filename, 'exec')

    function_finder = FunctionHeaderFinder()
    function_finder.visit(tree)

    for (name, header) in function_finder.headers.items():
        print(f"Function {name}:")
        print(f"    returns {header.returns}")
        for arg in header.args:
            print(f"    {arg[0]}: {arg[1]},")
        print()
    
    for (name, class_header) in function_finder.class_headers.items():
        print(f"Class {name}:")
        for base in class_header.bases:
            print(f"    baseclass: {base}")
        for (attr_name, attr_type) in class_header.instance_attributes.items():
            print(f"    {attr_name}: {attr_type}")
        if class_header.instance_attributes:
            print()
        for (method_name, method) in class_header.methods.items():
            print(f"    method: {method_name}")
            print(f"        returns {method.returns}")
            for arg in method.args:
                print(f"        {arg[0]}: {arg[1]},")
            print()
        print()

    output_file.close()
    sys.stdout = old_stdout

    ok = (os.path.isfile(baseline_filename) and 
        filecmp.cmp(baseline_filename, output_filename, shallow=False))
    if ok:
        print(f"test {filename} succeeded")
        os.remove(output_filename)
    else:
        print(f"test {filename} failed. Output file {output_filename} left in place.")

if __name__ == "__main__":
    test_headers("hello_world")
    test_headers("add_mult")
    test_headers("flow_of_control")
    test_headers("variables")
    test_headers("function_calls")
    test_headers("tuples")
    test_headers("lists")
    test_headers("sets")
    test_headers("dictionaries")
    test_headers("classes")
