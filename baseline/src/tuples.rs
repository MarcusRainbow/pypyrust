use std::collections::HashSet;
use std::collections::HashMap;
pub fn use_tuple_for_swap(mut a: i64, mut b: i64) -> i64 {
    if b > a {
        let tmp = (b, a);
        a = tmp.0;
        b = tmp.1;
    }
    return a - b;
}

pub fn return_tuple(a: i64, b: i64) -> (i64, i64) {
    return (a, b);
}

pub fn use_returned_tuple(a: i64, b: i64) -> i64 {
    let (c, d) = return_tuple(a, b);
    return use_tuple_for_swap(c, d);
}

pub fn tuple_in_args(mut a: (i64, i64)) -> i64 {
    if a.1 > a.0 {
        a = (a.1, a.0);
    }
    return a.0 - a.1;
}

