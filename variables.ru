fn assignment(mut a: bool, mut b: str, mut c: u32, mut d: u32) {
    let mut e = a;
    let mut f = b;
    let mut g = c;
    let mut h = c + d;
    let mut j = c + d + g + h;
    let mut k = k;
    let mut l = l;
}

fn annotated_assignment(mut a: bool, mut b: str, mut c: u32, mut d: u32) {
    let mut e: u32 = 3;
    let mut f: bool = a;
    let mut g: str = c;
    let mut h: u32 = c + d;
}

fn aug_assign(mut a: u32, mut b: u32) {
    let mut c = 0;
    c += a;
    c -= b;
    c /= a + b;
    c /= a;
    c *= b;
}

fn repeated_assign(mut a: str, mut b: str) -> str {
    let mut c = a;
    c = b;
    if b == a {
        c = "equal";
    }
    return c;
}

