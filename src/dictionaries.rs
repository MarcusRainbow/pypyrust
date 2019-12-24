use std::collections::HashMap;

pub fn create_dict(keys: &[String], values: &[String]) -> HashMap<String, String> {
    let d = keys.iter().cloned().zip(values.iter().cloned()).collect::<HashMap<_, _>>();
    return d;
}

pub fn access_dict(keys: &[String], dictionary: HashMap<String, String>) -> Vec<String> {
    let mut result = vec![];
    for key in keys {
        if dictionary.contains_key(key) {
            result.push(dictionary[key]);
        }
    }
    return result;
}

pub fn extend_dict(key: &str, value: &str, dictionary: HashMap<String, String>) {
    dictionary[key] = value.to_string();
}

pub fn static_dict() -> HashMap<String, i64> {
    let d = [
        ("foo".to_string(), 1),
        ("bar".to_string(), 2),
        ("wombat".to_string(), 3),
        ].iter().cloned().collect::<HashMap<_, _>>();
    return d;
}

pub fn dict_methods(mut dictionary: HashMap<String, String>) {
    let foobar = dictionary.get("foo").unwrap_or(&"bar".to_string()).clone();
    dictionary.clear();
    dictionary["foo"] = foobar.clone();
    assert!(dictionary.keys().position(|&tmp| tmp == "foo") != None);
    assert!(dictionary.values().position(|&tmp0| tmp0 == "bar") != None);
    for (k, v) in dictionary.iter() {
        println!("{} {} {}", k, ": ", v);
    }
    let mut d = dictionary.iter().collect::<HashMap<_, _>>();
    d.pop("foo", "bar");
    assert!(!d.contains_key("foo"));
    d.update(dictionary.iter());
    // TODO DELETE: d["foo"]
    let bar = d.setdefault("foo", "bar");
    assert!(bar == "bar");
    let (k, v) = d.popitem();
    assert!(k == "foo" && v == "bar");
}

