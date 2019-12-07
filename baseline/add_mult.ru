fn add_mult(a: i32, b: i32, c: i32) -> i32 {
    return a + b * c;
}

fn sub_div(a: i32, b: i32, c: i32) -> i32 {
    return a - b / c;
}

fn floor_div(a: i32, b: i32, c: i32) -> i32 {
    return a / (b % c);
}

fn bitwise(a: i32, b: i32, c: i32) -> i32 {
    return a << b & b >> c ^ (a | b);
}

fn powers(a: i32, b: i32, c: i32) -> i32 {
    return a * pow(a + b, pow(b + c, c + a));
}

fn unaries(a: i32, b: i32, c: i32) -> i32 {
    return !(~a + +b + -c) + ~~a;
}

fn boolean(a: bool, b: bool, c: bool) -> bool {
    return a && b && c || !(a || b || c);
}

fn compare(a: i32, b: i32, c: i32) -> bool {
    return a == b || b != c || a > b || c < a || a <= b || c >= b;
}

fn precedence(a: i32, b: i32, c: i32) -> bool {
    return a + (b - c) + (b + c) * a;
}

fn multi_compare(a: i32, b: i32, c: i32) -> bool {
    return (a < b) && (b < c) || (a >= b) && (b > c) || (a != b) && (b == c);
}

fn boolean_precedence(a: bool, b: bool, c: bool) -> bool {
    return a && b || c && b || a && c;
}

