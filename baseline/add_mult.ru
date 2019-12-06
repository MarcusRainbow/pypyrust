fn add_mult(mut a: u32, mut b: u32, mut c: u32) -> u32 {
    return a + b * c;
}

fn sub_div(mut a: u32, mut b: u32, mut c: u32) -> u32 {
    return a - b / c;
}

fn floor_div(mut a: u32, mut b: u32, mut c: u32) -> u32 {
    return a / (b % c);
}

fn bitwise(mut a: u32, mut b: u32, mut c: u32) -> u32 {
    return a << b & b >> c ^ (a | b);
}

fn powers(mut a: u32, mut b: u32, mut c: u32) -> u32 {
    return a * pow(a + b, pow(b + c, c + a));
}

fn unaries(mut a: u32, mut b: u32, mut c: u32) -> u32 {
    return !(~a + +b + -c) + ~~a;
}

fn boolean(mut a: bool, mut b: bool, mut c: bool) -> bool {
    return a && b && c || !(a || b || c);
}

fn compare(mut a: u32, mut b: u32, mut c: u32) -> bool {
    return a == b || b != c || a > b || c < a || a <= b || c >= b;
}

fn precedence(mut a: u32, mut b: u32, mut c: u32) -> bool {
    return a + (b - c) + (b + c) * a;
}

fn multi_compare(mut a: u32, mut b: u32, mut c: u32) -> bool {
    return (a < b) && (b < c) || (a >= b) && (b > c) || (a != b) && (b == c);
}

fn boolean_precedence(mut a: bool, mut b: bool, mut c: bool) -> bool {
    return a && b || c && b || a && c;
}

