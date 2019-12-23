use std::collections::HashSet;
use std::collections::HashMap;
pub fn create_set(a: i64, b: i64) -> HashSet<i64> {
    return (a..b).collect::<HashSet<_>>();
}

pub fn set_check_and_add(a: HashSet<String>, item: &str) -> bool {
    if a.contains(item) {
        return true;
    } else {
        a.insert(item.to_string());
        return false;
    }
}

pub fn create_static_set() -> HashSet<String> {
    let a = [
        "one",
        "two",
        "three",
        ].iter().cloned().collect::<HashSet<_>>();
    return a;
}

