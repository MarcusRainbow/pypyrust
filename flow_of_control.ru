fn if_else(mut a: bool, mut c: u32) -> u32 {
    if a {
        return c;
    } else {
        return 42;
    }
}

fn return_if_else(mut a: bool, mut c: u32) -> u32 {
    return if a { c } else { 42 };
}

fn if_elif_else(mut a: bool, mut b: bool, mut c: str, mut d: str) -> str {
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

fn while_loop(mut a: bool, mut b: bool) {
    while a || b {
        print("hello");
    }
}

fn while_break_continue(mut a: bool, mut b: bool) {
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

fn for_loop(mut a: u32, mut b: u32) -> u32 {
    let mut total = 0;
    for i in range(a, b) {
        total += i;
    }
    return total;
}

