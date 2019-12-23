use std::collections::HashSet;
use std::collections::HashMap;
pub fn add_mult(a: i64, b: i64, c: i64) -> i64 {
    return a + b * c;
}

pub fn sub_div(a: i64, b: i64, c: i64) -> i64 {
    return a - b / c;
}

pub fn floor_div(a: i64, b: i64, c: i64) -> i64 {
    return a / (b % c);
}

pub fn bitwise(a: i64, b: i64, c: i64) -> i64 {
    return a << b & b >> c ^ (a | b);
}

pub fn powers(a: i64, b: i64, c: i64) -> i64 {
    return a * (a + b).pow(((b + c).pow((c + a) as u32)) as u32);
}

pub fn unaries(a: i64, b: i64, c: i64) -> i64 {
    return !(!a + b + -c) + !!a;
}

pub fn boolean(a: bool, b: bool, c: bool) -> bool {
    return a && b && c || !(a || b || c);
}

pub fn compare(a: i64, b: i64, c: i64) -> bool {
    return a == b || b != c || a > b || c < a || a <= b || c >= b;
}

pub fn precedence(a: i64, b: i64, c: i64) -> i64 {
    return a + (b - c) + (b + c) * a;
}

pub fn multi_compare(a: i64, b: i64, c: i64) -> bool {
    return (a < b) && (b < c) || (a >= b) && (b > c) || (a != b) && (b == c);
}

pub fn boolean_precedence(a: bool, b: bool, c: bool) -> bool {
    return a && b || c && b || a && c;
}

