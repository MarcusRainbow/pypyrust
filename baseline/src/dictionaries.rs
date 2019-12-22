pub fn create_dict(keys: &[&str], values: &[&str]) -> HashMap<String, String> {
    let d = keys.iter().zip(values.iter()).collect::<HashMap<_>>();
    return d;
}

pub fn access_dict(keys: &[&str], dictionary: HashMap<&str, &str>) -> Vec<String> {
    let result = [];
    for key in keys {
        if dictionary.contains(key) {
            result.append(dictionary[key]);
        }
    }
    return result;
}

pub fn extend_dict(key: &str, value: &str, dictionary: HashMap<&str, &str>) {
    dictionary[key] = value.to_string();
}

pub fn static_dict() -> HashMap<String, String> {
    let d = [
        ("foo", 1),
        ("bar", 2),
        ("wombat", 3),
        ].iter().cloned().collect::<HashMap<_>>();
    return d;
}

pub fn dict_methods(dictionary: HashMap<&str, &str>) {
    let foobar = dictionary.get("foo", "bar").to_string();
    dictionary.clear();
    dictionary["foo"] = foobar;
    assert!(dictionary.keys().contains("foo"));
    assert!(dictionary.values().contains("bar"));
    for (k, v) in dictionary.items() {
        println!(k": "v);
    }
    let d = dict(dictionary.items());
    d.pop("foo", "bar");
    assert!(!d.contains("foo"));
    d.update(dictionary.items());
    // TODO DELETE: d["foo"]
    let bar = d.setdefault("foo", "bar").to_string();
    assert!(bar == "bar");
    let (k, v) = d.popitem();
    assert!(k == "foo" && v == "bar");
}

