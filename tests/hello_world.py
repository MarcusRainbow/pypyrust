def hello():
    print("hello world!")

def hello_override_end():
    print("hello ", end='')
    print("world!", end='')
    print()

def hello_multi():
    print("hello", "world!")

def hello_multi_override_sep():
    print("hello", "world!", sep='_')

def hello_multi_override_end():
    print("hello", "world", sep='_', end='!\n')

def hello_override_end_non_empty():
    print("hello world", end="!\n")

# def hello_formatted():
#     w = "world"
#     print(f"hello {w}")

