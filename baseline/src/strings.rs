fn str_str_string(a: &str, b: &str) -> String {
    let c: String = a.to_string();
    let d = b.to_string();
    let e = str_string(a);
    let f = str_string(a);
    if c == d && e == f {
        return a.to_string();
    } else {
        return c;
    }
}

fn str_string(a: &str) -> String {
    return a.to_string();
}

fn str_str_op(a: &str, b: &str) -> String {
    let c = a.to_string() + b;
    let mut d = a.to_string();
    d += "foo";
    return c + &d + "bar";
}

pub fn invoke_all() {
   let a = str_str_string("foo", "bar");
   let b = str_string("foo");
   let c = str_str_op("foo", "bar");
   print!("{} {} {}", a, b, c);
}
