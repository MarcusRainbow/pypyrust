pub fn create_list(a: i64, b: i64) -> &[i64] {
    return a..b.map(x| x * x.collect::<Vec<_>>();
}

pub fn process_list(a: &[i64], b: &[i64]) -> &[i64] {
    return zip(a, b).map((x, y)| (x, y).collect::<Vec<_>>();
}

pub fn add_mult_lists(a: &[f64], b: &[f64], c: &[f64]) -> &[f64] {
    let d = (a + b) * c;
    return d;
}

pub fn manual_iterator(a: &[f64]) -> (f64, f64) {
    let mut sum = 0.0;
    let mut prod = 1.0;
    for i in a {
        sum += a[i];
        prod *= a[i];
    }
    return (sum, prod);
}

pub fn manual_dot_product(a: &[f64], b: &[f64]) -> f64 {
    let mut sum = 0;
    for (i, j) in zip(a, b) {
        sum += i * j;
    }
    return sum;
}

