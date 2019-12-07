fn if_else(a: bool, c: i32) -> i32 {
    if a {
        return c;
    } else {
        return 42;
    }
}

fn return_if_else(a: bool, c: i32) -> i32 {
    return if a { c } else { 42 };
}

fn if_elif_else(a: bool, b: bool, c: str, d: str) -> str {
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
        print("hello");
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
        print("hello");
    }
}

fn for_loop(a: i32, b: i32) -> i32 {
    let mut total = 0;
    for i in range(a, b) {
        total += i;
    }
    return total;
}

