import ast
import sys
import os
import filecmp
from typing import Dict
from var_utils import type_from_annotation

class FunctionHeader:
    def __init__(self, returns: str, args: [(str, str)]):
        self.returns = returns
        self.args = args

class FunctionHeaderFinder(ast.NodeVisitor):
    """
    Given an AST representing a module, find all the function
    definitions and record the return types.
    """

    def __init__(self):
        self.headers : Dict[str, FunctionHeader] = {}

    def visit_FunctionDef(self, node):
        name = node.name
        returns = type_from_annotation(node.returns, f"{name} return", True)
        args = []
        for arg in node.args.args:
            argname = arg.arg
            typed = type_from_annotation(arg.annotation, f"{name}: {argname}", False)
            args.append((argname, typed))
        
        self.headers[name] = FunctionHeader(returns, args)

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
    # test_headers("classes")
