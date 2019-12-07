fn add_mult(a: i64, b: i64, c: i64) -> i64 {
    return a + b * c;
}

fn sub_div(a: i64, b: i64, c: i64) -> i64 {
    return a - b / c;
}

fn floor_div(a: i64, b: i64, c: i64) -> i64 {
    return a / (b % c);
}

fn bitwise(a: i64, b: i64, c: i64) -> i64 {
    return a << b & b >> c ^ (a | b);
}

fn powers(a: i64, b: i64, c: i64) -> i64 {
    return a * (a + b).pow(((b + c).pow((c + a) as u32)) as u32);
}

fn unaries(a: i64, b: i64, c: i64) -> i64 {
    return !(!a + b + -c) + !!a;
}

fn boolean(a: bool, b: bool, c: bool) -> bool {
    return a && b && c || !(a || b || c);
}

fn compare(a: i64, b: i64, c: i64) -> bool {
    return a == b || b != c || a > b || c < a || a <= b || c >= b;
}

fn precedence(a: i64, b: i64, c: i64) -> i64 {
    return a + (b - c) + (b + c) * a;
}

fn multi_compare(a: i64, b: i64, c: i64) -> bool {
    return (a < b) && (b < c) || (a >= b) && (b > c) || (a != b) && (b == c);
}

fn boolean_precedence(a: bool, b: bool, c: bool) -> bool {
    return a && b || c && b || a && c;
}

