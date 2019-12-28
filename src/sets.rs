use std::collections::HashSet;

pub fn create_set(a: i64, b: i64) -> HashSet<i64> {
    return (a..b).collect::<HashSet<_>>();
}

pub fn set_check_and_add(a: &mut HashSet<String>, item: &str) -> bool {
    if a.contains(item) {
        return true;
    } else {
        a.insert(item.to_string());
        return false;
    }
}

pub fn create_static_set() -> HashSet<String> {
    let a = [
        "one".to_string(),
        "two".to_string(),
        "three".to_string(),
        ].iter().cloned().collect::<HashSet<_>>();
    return a;
}

pub fn set_methods(a: i64, b: &str) {
    let mut s_int = (0..a).collect::<HashSet<_>>();
    let mut s_str = (0..a).map(|x| b.repeat(x as usize)).collect::<HashSet<_>>();
    s_int.insert(a);
    s_str.insert("foo".to_string());
    let mut copy_s_int = s_int.clone();
    assert!(copy_s_int == s_int);
    assert!(&copy_s_int as *const _ != &s_int as *const _);
    let mut diff_s_int = s_int.difference(&copy_s_int).cloned().collect::<HashSet<i64>>();
    assert!(diff_s_int.len() == 0);
    copy_s_int.clear();
    assert!(copy_s_int != s_int);
    diff_s_int.clear();
    // TODO difference_update(s_int);
    assert!(diff_s_int == s_int);
    s_int.remove(&0);
    s_str.remove("baz");
    let union_s_int = s_int.union(&copy_s_int).cloned().collect::<HashSet<i64>>();
    assert!(copy_s_int == union_s_int);
    let mut inter_s_int = s_int.intersection(&copy_s_int).cloned().collect::<HashSet<i64>>();
    s_int.clear();
    // TODO intersection_update(copy_s_int, inter_s_int);
    assert!(s_int != inter_s_int);
    assert!(!s_int.is_disjoint(&inter_s_int));
    assert!(inter_s_int.is_subset(&s_int));
    assert!(s_int.is_superset(&inter_s_int));
    let sd_s_int = s_int.symmetric_difference(&copy_s_int).cloned().collect::<HashSet<i64>>();
    s_int.clear();
    // TODO symmetric_difference_update(copy_s_int, sd_s_int);
    s_int.remove(&0);
    s_int.remove(&1);
    s_str.remove("foo");
}

