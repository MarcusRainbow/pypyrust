pub fn if_else(a: bool, c: i64) -> i64 {
    if a {
        return c;
    } else {
        return 42;
    }
}

pub fn return_if_else(a: bool, c: i64) -> i64 {
    return if a { c } else { 42 };
}

pub fn if_elif_else(a: bool, b: bool, c: &str, d: &str) -> String {
    if a && b {
        return c.to_string();
    } else {
        if a || b {
            return d.to_string();
        } else {
            return "Neither".to_string();
        }
    }
}

pub fn while_loop(a: bool, b: bool) {
    while a || b {
        println!("hello");
    }
}

pub fn while_break_continue(a: bool, b: bool) {
    while true {
        if a {
            break;
        } else {
            if b {
                continue;
            }
        }
        println!("hello");
    }
}

pub fn for_loop(a: i64, b: i64) -> i64 {
    let mut total = 0;
    for i in a..b {
        total += i;
    }
    return total;
}

