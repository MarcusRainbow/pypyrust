use std::collections::HashSet;
use std::collections::HashMap;
pub fn hello() {
    println!("hello world!");
}

pub fn hello_override_end() {
    print!("hello ");
    print!("world!");
    println!();
}

pub fn hello_multi() {
    println!("{} {}", "hello", "world!");
}

pub fn hello_multi_override_sep() {
    println!("{}_{}", "hello", "world!");
}

pub fn hello_multi_override_end() {
    print!("{}_{}!\n", "hello", "world");
}

pub fn hello_override_end_non_empty() {
    print!("{}!\n", "hello world");
}

