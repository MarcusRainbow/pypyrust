"""
The top-level compiler module for PyPyRust. It takes a Python source
file and generates a Rust source file, representing the Python.
"""

import ast
import sys
from rust_generator import RustGenerator
from dependency_analyser import DependencyAnalyser
from var_analyser import FunctionHeaderFinder

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

    # Find the local header definitions
    ff = FunctionHeaderFinder()
    ff.visit(tree)

    # Write the header
    dependencies = DependencyAnalyser(ff.headers)
    dependencies.visit(tree)
    dependencies.write_preamble()

    # Walk the tree, outputting Rust code as we go (rather like XSLT)
    RustGenerator(ff.headers, ff.class_headers).visit(tree)

    return True

def compile_file_to_rust(filename: str) -> bool:
    """
    Compiles a Python source file, generating Rust source in
    stdout that does the same thing. Warnings and compiler errors are
    sent to stderr. Returns a bool which is True if the compilation
    was successful (no errors, though there may have been warnings).

    filename is the file containing the Python source.
    """
    file = open(filename, 'r')
    source = file.read()
    file.close()
    ok = compile_to_rust(source, filename)
    assert(ok)

if __name__ == "__main__":
    # if len(sys.argv) != 2:
    #     print(f"usage: {sys.argv[0]} <file_to_compile>", file=sys.stderr)
    #     exit(1)

    # compile_file_to_rust(sys.argv[1])

    compile_file_to_rust("../pdl-sandbox/src/ImpliedVolHints.py")