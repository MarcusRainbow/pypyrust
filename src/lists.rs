pub fn create_list(a: i64, b: i64) -> Vec<i64> {
    return (a..b).map(|x| (x * x)).collect::<Vec<_>>();
}

pub fn process_list(a: &[i64], b: &[i64]) -> Vec<(i64, i64)> {
    return a.iter().zip(b.iter()).map(|(&x, &y)| (x, y)).collect::<Vec<_>>();
}

pub fn add_mult_lists(a: &[f64], b: &[f64], c: &[f64]) -> Vec<f64> {
    let d = a.iter().zip(b.iter().zip(c.iter())).map(|(a,(b, c))|
        (a + b) * c
        ).collect::<Vec<_>>();
    return d;
}

pub fn manual_iterator(a: &[f64]) -> (f64, f64) {
    let mut sum = 0.0;
    let mut prod = 1.0;
    for i in a {
        sum += i;
        prod *= i;
    }
    return (sum, prod);
}

pub fn manual_dot_product(a: &[f64], b: &[f64]) -> f64 {
    let mut sum = 0.0;
    for (i, j) in a.iter().zip(b.iter()) {
        sum += i * j;
    }
    return sum;
}

pub fn static_lists(a: i64) -> bool {
    let odd = [
        1,
        3,
        5,
        7,
        ];
    return odd.iter().position(|&tmp| tmp == a) != None;
}

