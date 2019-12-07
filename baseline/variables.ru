fn assignment(a: bool, b: str, c: i64, d: i64) -> i64 {
    let e = a;
    let f = b;
    let g = c;
    let h = c + d;
    let j = c + d + g + h;
    let k =  = j;
    let l =  = j;
    return if a { e + f + j + k + l } else { 0 };
}

fn annotated_assignment(a: bool, b: str, c: i64, d: i64) -> i64 {
    let e: i64 = 3;
    let f: bool = a;
    let g: str = c;
    let h: i64 = c + d;
    return if a && f && g == "hello" { e + h } else { 0 };
}

fn aug_assign(a: i64, b: i64) -> i64 {
    let mut c = 0;
    c += a;
    c -= b;
    c /= a + b;
    c /= a;
    c *= b;
    return c;
}

fn repeated_assign(a: str, b: str) -> str {
    let mut c = a;
    c = b;
    if b == a {
        c = "equal";
    }
    return c;
}

fn pathological(a: bool, b: str, c: str) -> str {
    let mut d: str = "";
    if a {
        d = b;
    } else {
        d = c;
    }
    return d;
}

