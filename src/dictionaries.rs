use std::collections::HashMap;
pub fn create_dict(keys: &[String], values: &[String]) -> HashMap<String, String> {
    let d = keys.iter().zip(values.iter()).collect::<HashMap<_, _>>();
    return d;
}

pub fn access_dict(keys: &[String], dictionary: HashMap<String, String>) -> Vec<String> {
    let result = [];
    for key in keys {
        if dictionary.contains_key(key) {
            result.append(dictionary[key]);
        }
    }
    return result;
}

pub fn extend_dict(key: &str, value: &str, dictionary: HashMap<String, String>) {
    dictionary[key] = value.to_string();
}

pub fn static_dict() -> HashMap<String, String> {
    let d = [
        ("foo", 1),
        ("bar", 2),
        ("wombat", 3),
        ].iter().cloned().collect::<HashMap<_, _>>();
    return d;
}

pub fn dict_methods(dictionary: HashMap<String, String>) {
    let foobar = dictionary.get("foo").unwrap_or("bar");
    dictionary.clear();
    dictionary["foo"] = foobar;
    assert!(dictionary.keys().position(|&tmp| tmp == "foo") != None);
    assert!(dictionary.values().position(|&tmp0| tmp0 == "bar") != None);
    for (k, v) in dictionary {
        println!("{} {} {}", k, ": ", v);
    }
    let d = dictionary.collect::<HashMap<_, _>>();
    d.pop("foo", "bar");
    assert!(!d.contains_key("foo"));
    d.update(dictionary);
    // TODO DELETE: d["foo"]
    let bar = d.setdefault("foo", "bar");
    assert!(bar == "bar");
    let (k, v) = d.popitem();
    assert!(k == "foo" && v == "bar");
}

