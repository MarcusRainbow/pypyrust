fn hello() {
    println!("hello world!");
}

fn hello_override_end() {
    print!("hello ");
    print!("world!");
    println!();
}

fn hello_multi() {
    println!("{} {}", "hello", "world!");
}

fn hello_multi_override_sep() {
    println!("{}_{}", "hello", "world!");
}

fn hello_multi_override_end() {
    print!("{}_{}!\n", "hello", "world");
}

fn hello_override_end_non_empty() {
    print!("{}!\n", "hello world");
}

