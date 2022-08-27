"""
Module supporting analysis of which types we are using.
Results in a set of use statements at the head of a Rust
source file.
"""

from typing import Dict
import ast
import sys
import filecmp
import os
from var_analyser import FunctionHeader

class DependencyAnalyser(ast.NodeVisitor):
    """
    Visitor of the Python AST which analyses usage of standard
    library types like HashMap and HashSet. Results are retained 
    internally.
    """

    def __init__(self, headers: Dict[str, FunctionHeader]):
        self.wants_hashmap = False
        self.wants_hashset = False
        
        for func in headers.values():
            self.check_dependencies(func.returns)
            for arg in func.args:
                self.check_dependencies(arg[1])

    def check_dependencies(self, text: str):
        if text.find("HashMap") != -1:
            self.wants_hashmap = True
        if text.find("HashSet") != -1:
            self.wants_hashset = True

    def write_preamble(self):
        """
        Write to stdout a header for the output file, pulling in
        any standard dependencies.
        """
        if self.wants_hashset:
            print("use std::collections::HashSet;")
        if self.wants_hashmap:
            print("use std::collections::HashMap;")
        if self.wants_hashmap or self.wants_hashset:
            print()

    def visit_Set(self, node):
        self.wants_hashset = True
        for element in node.elts:
            self.visit(element)

    def visit_Dict(self, node):
        self.wants_hashmap = True
        for key in node.keys:
            self.visit(key)
        for value in node.values:
            self.visit(value)

    def visit_SetComp(self, node):
        self.wants_hashset = True
        for generator in node.generators:
            self.visit(generator)
        self.visit(node.elt)

    def visit_DictComp(self, node):
        self.wants_hashmap = True
        for generator in node.generators:
            self.visit(generator)
        self.visit(node.key)
        self.visit(node.value)

    def visit_Call(self, node):
        """
        Check for the "dict" function, which creates a HashMap
        """
        for a in node.args:
            self.visit(a)

        if isinstance(node.func, ast.Name) and node.func.id == "dict":
            self.wants_hashmap = True
