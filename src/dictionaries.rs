use std::collections::HashMap;

pub fn create_dict(keys: &[String], values: &[String]) -> HashMap<String, String> {
    let d = keys.iter().cloned().zip(values.iter().cloned()).collect::<HashMap<_, _>>();
    return d;
}

pub fn access_dict(keys: &[String], dictionary: HashMap<String, String>) -> Vec<String> {
    let mut result = vec![];
    for key in keys {
        if dictionary.contains_key(key) {
            result.push(dictionary[key].clone());
        }
    }
    return result;
}

pub fn extend_dict(key: &str, value: &str, dictionary: &mut HashMap<String, String>) {
    dictionary.insert(key.to_string(), value.to_string());
}

pub fn static_dict() -> HashMap<String, i64> {
    let d = [
        ("foo".to_string(), 1),
        ("bar".to_string(), 2),
        ("wombat".to_string(), 3),
        ].iter().cloned().collect::<HashMap<_, _>>();
    return d;
}

pub fn dict_methods(dictionary: &mut HashMap<String, String>) {
    let foobar = dictionary.get("foo").unwrap_or(&"bar".to_string()).clone();
    dictionary.clear();
    dictionary.insert("foo".to_string(), foobar.clone());
    assert!(dictionary.keys().position(|tmp| tmp == "foo") != None);
    assert!(dictionary.values().position(|tmp0| tmp0 == "bar") != None);
    for (k, v) in dictionary.iter().map(|(ref k, ref v)| ((*k).clone(), (*v).clone())) {
        println!("{} {} {}", k, ": ", v);
    }
    let mut d = dictionary.iter().map(|(ref k, ref v)| ((*k).clone(), (*v).clone())).collect::<HashMap<_, _>>();
    let mut bar = d.remove("foo").unwrap_or("bar".to_string());
    assert!(!d.contains_key("foo"));
    assert!(bar == "bar");
    d.extend(dictionary.iter().map(|(ref k, ref v)| ((*k).clone(), (*v).clone())));
    d.remove("foo");
    let l = d.len();
    assert!(l == 0);
    bar = d.entry("foo".to_string()).or_insert("bar".to_string()).clone();
    assert!(bar == "bar");
    let (k, v) = d.drain().next().unwrap();
    assert!(k == "foo" && v == "bar");
}

