pub fn assignment(a: bool, b: &str, c: i64, d: i64) -> i64 {
    let e = a;
    let f = b.to_string();
    let g = c;
    let h = c + d;
    let j = c + d + g + h;
    let k = j;
    let l = j;
    return if a && e || f == "hello" { j + k + l } else { 0 };
}

pub fn annotated_assignment(a: bool, b: &str, c: i64, d: i64) -> i64 {
    let e: i64 = 3;
    let f: bool = a;
    let g: String = b.to_string();
    let h: i64 = c + d;
    return if a && f && g == "hello" { e + h } else { 0 };
}

pub fn aug_assign(a: i64, b: i64) -> i64 {
    let mut c = 0;
    c += a;
    c -= b;
    c /= a + b;
    c /= a;
    c *= b;
    return c;
}

pub fn repeated_assign(a: &str, b: &str) -> String {
    let mut c = a.to_string();
    c = b.to_string();
    if b == a {
        c = "equal".to_string();
    }
    return c;
}

pub fn pathological(a: bool, b: &str, c: &str) -> String {
    let mut d: String = String::new();
    if a {
        d = b.to_string();
    } else {
        d = c.to_string();
    }
    return d;
}

