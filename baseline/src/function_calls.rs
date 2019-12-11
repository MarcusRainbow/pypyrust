pub fn call_add_mult(a: i64, b: i64, c: i64) -> i64 {
    let d = ::add_mult::add_mult(a, b, c);
    let e = ::add_mult::sub_div(a, b, c);
    return d + e;
}

pub fn call_flow_of_control(a: bool, b: i64) -> i64 {
    let c = ::flow_of_control::if_else(a, b);
    let d = ::flow_of_control::return_if_else(a, b);
    let e = ::flow_of_control::if_elif_else(a, !a, "hello", "world");
    ::flow_of_control::while_loop(a, !a);
    return if e == "Foo" { c } else { d };
}

pub fn call_local(a: i64, b: i64, c: i64) -> i64 {
    if a > 0 {
        return call_local(a - 1, b, c);
    } else {
        return call_add_mult(a, b, c);
    }
}

