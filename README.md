# PyPyRust

_A Python-implemented Python to Rust compiler_

Python is the world's most popular language, in part because it is so easy to write. Rust
is arguably the world's best general-purpose language: it is fast, with concise syntax
and rigorous safety rules. Moreover, it has features that make it potentially good for
replicating Python. It supports functional and object-oriented programming, though without
inheritance. Its traits are similar to interfaces in Python, though it does not support
duck typing (if it waddles like a duck and quacks like a duck, it is a duck).

## Restrictions on the Python side

Python natively uses variants for everything, where a variant can be an integer, float,
complex, boolean, string, tuple, list, set or dict. (Objects are semantic sugar around
dicts.) It would be possible to compile Python into Rust code that used variants in the
same way, and this is how Cython by default compiles Python into C code. However, the
resulting Rust code would be horrible both to read and to execute, being only a few times
quicker than CPython.

We therefore require the Python code to be supplied with sufficient type hints to allow
the Rust compiler to recognise which Rust types to use. Rust is clever enough to deduce
types where they are not ambiguous, so really only the function headers need hinting.

Rust does not support execution of arbitrary code fragments, so this is not supported in
Python either. In practice, Python tends not to be written like this anyway, and Python
is written in modules, with all the code exported in functions or classes.

## Restrictions on the Rust side

One of the things that makes Rust so fast is that it allows programmers to manage the
lifetime of objects in a safe way. In comparison, C is as flexible, allowing items to be
allocated statically, on the stack or the heap, but C is not at all safe, allowing stack
items to be accessed after they cease to exist, and allowing heap items to be deleted
multiple times or not at all. In contrast, Python is safe but not at all flexible -- all items
are represented by the same type of variant, which is initially allocated on the stack but
has internal pointers that refer to items, including other variants, which are allocated
on a garbage-collected heap.

In compiling Python to Rust, we cannot reproduce the richness of Rust lifetimes. We represent
those items that Python would allocate on the heap as Rust heap-items, which must be garbage
collected. Rust has no built-in garbage collector. There is a third-party garbage collector
implementation, shifgrethor, which we can experiment with. For now, we just use reference
counting, and cross our fingers about circular references.

## Interoperability

One of the main design features of Cython, and in fact the main thing that slows it down, is
that Cython code (Python code compiled with Cython into C code, and then compiled into
binary object code) is 100% interoperable with Python. You can use Cython on some of your
modules but not others, and you can mix libraries that were compiled with Cython with those
that are just interpreted Python.

Pypyrust is not like this. It compiles Python into native Rust code, without interoperability
wrappers. If you want interoperability between Pypyrust modules and Python modules or libraries,
you have to design and write the iterop layer. (An obvious extension to Pypyrust is to
auto-generate this interop layer. We leave this as an exercise.)
