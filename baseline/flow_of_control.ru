fn if_else(a: bool, c: i64) -> i64 {
    if a {
        return c;
    } else {
        return 42;
    }
}

fn return_if_else(a: bool, c: i64) -> i64 {
    return if a { c } else { 42 };
}

fn if_elif_else(a: bool, b: bool, c: &str, d: &str) -> String {
    if a && b {
        return c;
    } else {
        if a || b {
            return d;
        } else {
            return "Neither";
        }
    }
}

fn while_loop(a: bool, b: bool) {
    while a || b {
        println!("hello");
    }
}

fn while_break_continue(a: bool, b: bool) {
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

fn for_loop(a: i64, b: i64) -> i64 {
    let mut total = 0;
    for i in a..b {
        total += i;
    }
    return total;
}

