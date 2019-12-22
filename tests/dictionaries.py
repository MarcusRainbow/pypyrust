from typing import List, Dict

def create_dict(keys: List[str], values: List[str]) -> Dict[str, str]:
    d = { k: v for k, v in zip(keys, values)}
    return d

def access_dict(keys: List[str], dictionary: Dict[str, str]) -> List[str]:
    result = []
    for key in keys:
        if key in dictionary:
            result.append(dictionary[key])
    return result

def extend_dict(key: str, value: str, dictionary: Dict[str, str]):
    dictionary[key] = value

def static_dict() -> Dict[str, str]:
    d = {"foo": 1, "bar": 2, "wombat": 3}
    return d

def dict_methods(dictionary: Dict[str, str]):

    foobar = dictionary.get("foo", "bar")
    dictionary.clear()
    dictionary["foo"] = foobar
    assert("foo" in dictionary.keys())
    assert("bar" in dictionary.values())

    for k, v in dictionary.items():
        print(f"{k}: {v}")

    d = dict(dictionary.items())

    d.pop("foo", "bar")
    assert("foo" not in d)
    d.update(dictionary.items())

    del d["foo"]

    bar = d.setdefault("foo", "bar")
    assert(bar == "bar")

    (k, v) = d.popitem()
    assert(k == "foo" and v == "bar")
