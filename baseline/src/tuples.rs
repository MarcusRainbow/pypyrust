pub fn use_tuple_for_swap(mut a: i64, mut b: i64) -> i64 {
    if b > a {
        let mut (a, b) = (b, a);
    }
    return a - b;
}

pub fn return_tuple(a: i64, b: i64) -> (i64, i64) {
    return (a, b);
}

pub fn use_returned_tuple(a: i64, b: i64) -> i64 {
    let mut (c, d) = return_tuple(a, b);
    return use_tuple_for_swap(c, d);
}

pub fn tuple_in_args(a: (i64, i64)) -> i64 {
    if a[1] > a[0] {
        let mut (a[0], a[1]) = (a[1], a[0]);
    }
    return a[0] - a[1];
}

