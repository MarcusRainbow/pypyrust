from typing import List, Dict
import sys
import ast

MATCHING_BRACKETS = {
    "(": ")", ")": "(",
    "[": "]", "]": "[",
    "{": "}", "}": "{",
    "<": ">", ">": "<",
}

UNKNOWN_TYPE = "Unknown"

# Mapping from pair of Rust types (e.g. a binary op) to Rust type
TYPE_COERCIONS = {
    ("bool", "i64"): "i64",
    ("i64", "bool"): "i64",
    ("bool", "f64"): "f64",
    ("f64", "bool"): "f64",
    ("i64", "f64"): "f64",
    ("f64", "i64"): "f64",
    ("Vec<", "&["): "Vec<",
    ("&[", "Vec<"): "Vec<",
    ("&str", "i64"): "String",
    ("i64", "&str"): "String",
    ("String", "i64"): "String",
    ("i64", "String"): "String",
}

# Mapping from Python type to Rust equivalent (arg type)
TYPE_MAPPING = {
    "bool": "bool",
    "int": "i64",
    "long": "i64",
    "float": "f64",
    "str": "&str",
}

CONTAINER_CONVERSIONS = {
    "&str": ".to_string()",
    "&String": ".clone()"
}

def strip_container(text: str) -> str:
    return text[find_container(text): -1]

def extract_container(text: str) -> str:
    return text[0:find_container(text)]

def dict_type_from_list(text: str) -> str:
    key_value_tuple = strip_container(text)
    key_value = strip_container(key_value_tuple)
    return f"HashMap<{key_value}>"

def detemplatise(text: str) -> str:
    left = text.find("<")
    right = text.rfind(">")
    if left < 0 or right < 0:
        return text
    return f"{text[:left]}<_>{text[right + 1:]}"

def dereference(text: str) -> str:
    while text[0] == "&":
        text = text[1:]
    return text

def extract_types(text: str) -> List[str]:
    left = text.find("<")
    right = text.rfind(">")
    if left < 0 or right < 0:
        return []
    types = text[left + 1 : right]
    return types.split(", ")    

def find_container(text: str) -> int:
    """
    Finds the initial part of the string that represents the
    container, and return a pointer to just after it.

    If not found, returns zero
    """
    if len(text) < 2:
        return 0
    last = text[-1]
    if last not in MATCHING_BRACKETS:
        return 0
    matching = MATCHING_BRACKETS[last]
    if matching not in text:
        return 0
    return text.index(matching) + 1

def is_string(text: str) -> bool:
    """
    Does the given type represent a string?
    """
    return text == "&str" or text == "String"

def is_int(text: str) -> bool:
    """
    Does the given type represent an int?
    """
    return text == "i64"

def is_list(text: str) -> bool:
    """
    Does the given type represent a list?
    """
    return text[-1] == "]" or text[:4] == "Vec<"

def is_dict(text: str) -> bool:
    """
    Does the given type represent a dictionary?
    """
    return text[:8] == "HashMap<"

def is_reference_type(text: str) -> bool:
    """
    Does the given type represent a reference type?
    """
    return text[0] == "&"

def is_iterator_type(text: str) -> bool:
    """
    Does the given type represent an iterator?
    """
    # TODO we need much tidier handling of iterators
    return text[0] == "["

def numeric_type(node: ast.Num) -> str:
    python_type = type(node.n).__name__
    if python_type == 'int' or python_type == 'long':
        return "i64"
    elif python_type == 'float':
        return "f64"
    else:
        raise Exception(f"Unsupported numeric type: {python_type}")

def type_from_annotation(annotation, arg: str, container: bool) -> str:
    if annotation is None:
        if arg == "self":
            return ""
        else:
            print(f"missing type annotation for argument '{arg}'", file=sys.stderr)
            return 'None'
    elif isinstance(annotation, str):
        id = annotation
    elif isinstance(annotation, ast.Name):
        id = annotation.id
    elif isinstance(annotation, type):
        id = annotation.__name__
    elif isinstance(annotation, ast.Subscript):
        return type_from_subscript(annotation, arg, container)
    else:
        print(f"unexpected type of annotation for argument '{arg}'", file=sys.stderr)
        return 'None'
        
    if id in TYPE_MAPPING:
        arg_type = TYPE_MAPPING[id]
        return container_type(arg_type) if container else arg_type
    else:
        # assume this is a locally defined type such as a Class. If a
        # container type is required, return the type itself. Otherwise
        # a reference.
        return id if container else f"&{id}"

def type_from_subscript(annotation: ast.Subscript, arg: str, container: bool) -> str:
    """
    Return a type that is a Tuple, List, Dictionary, Set
    """
    outer_type = annotation.value.id
    if outer_type == "Tuple":
        start, end = "(", ")"
    elif outer_type == "List":
        start, end = "&[", "]"
    elif outer_type == "Set":
        start, end = "HashSet<", ">"
    elif outer_type == "Dict":
        start, end = "HashMap<", ">"
    else:
        start, end = "<unknown>", "</unknown>"

    # We always want the types within a container to be container
    # types themselves. List<&str> is legal Rust, but a pain to
    # handle in terms of lifetimes.

    type_def = annotation.slice.value
    if isinstance(type_def, ast.Name):
        types = type_from_annotation(type_def, arg, True)
    elif isinstance(type_def, ast.Tuple):
        type_str = [type_from_annotation(e, arg, True)
            for e in type_def.elts]
        types = ', '.join(type_str)
    elif isinstance(type_def, ast.Subscript):
        types = type_from_annotation(type_def, arg, True)
    
    result = f"{start}{types}{end}"
    return container_type(result) if container else result

def merge_types(current_type: str, typed: str) -> str:
    if not typed:
        return current_type
    elif not current_type:
        return typed
    elif current_type == typed:
        return current_type
    elif (current_type, typed) in TYPE_COERCIONS:
        return TYPE_COERCIONS[(current_type, typed)]

    # if this is a container type and we are matching a container
    curr_ctr = extract_container(current_type)
    given_ctr = extract_container(typed)
    if (curr_ctr, given_ctr) not in TYPE_COERCIONS:
        return UNKNOWN_TYPE
    
    curr_subtypes = strip_container(current_type).split(", ")
    given_subtypes = strip_container(typed).split(", ")
    if len(curr_subtypes) != len(given_subtypes):
        print("Warning: cannot merge subtypes of different lengths", file=sys.stderr)
    subtypes = []
    for curr, given in zip(curr_subtypes, given_subtypes):
        subtypes.append(merge_types(curr, given))
    
    ctr = TYPE_COERCIONS[(curr_ctr, given_ctr)]
    terminator = MATCHING_BRACKETS[ctr[-1]]
    return ctr + ", ".join(subtypes) + terminator

def container_type(arg_type: str) -> str:
    """
    Given an arg type (the sort of type that is passed as a
    function arg) return a container type (the sort of type that
    is returned from a function, or used as a variable).
    """
    if arg_type == "&str":
        return "String"
    elif len(arg_type) == 0:
        return ""
    elif arg_type[-1] == "]":
        return f"Vec<{strip_container(arg_type)}>"
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
