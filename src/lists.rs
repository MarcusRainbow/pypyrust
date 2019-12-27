pub fn create_list(a: i64, b: i64) -> Vec<i64> {
    return (a..b).map(|x| (x * x)).collect::<Vec<_>>();
}

pub fn process_list(a: &[i64], b: &[i64]) -> Vec<(i64, i64)> {
    return a.iter().cloned().zip(b.iter().cloned()).map(|(x, y)| (x, y)).collect::<Vec<_>>();
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
    for (i, j) in a.iter().cloned().zip(b.iter().cloned()) {
        sum += i * j;
    }
    return sum;
}

pub fn static_lists(a: i64) -> bool {
    let odd = vec![
        1,
        3,
        5,
        7,
        ];
    return odd.iter().position(|&tmp| tmp == a) != None;
}

pub fn list_methods(a: i64, b: &str) {
    let mut l_int = (0..a).collect::<Vec<_>>();
    let mut l_str = (0..a).map(|x| b.repeat(x as usize)).collect::<Vec<_>>();
    l_int.push(a);
    l_str.push("foo".to_string());
    l_int.insert(0, a);
    l_str.insert(2, b.to_string());
    l_int.extend(vec![a, (a + 1)]);
    l_str.extend(vec![b.to_string()]);
    assert!(l_int.iter().sum::<i64>() > 0);
    assert!(l_str.iter().filter(|&x| x == "foo").count() > 0);
    let i = l_int.iter().position(|&x| x == a).unwrap();
    let j = l_str.iter().position(|ref x| *x == b).unwrap();
    assert!(i >= j);
    assert!(l_int.iter().min().unwrap() <= l_int.iter().max().unwrap());
    l_int.reverse();
    l_str.sort();
    let x_int = l_int.pop().unwrap();
    let x_str = l_str.pop().unwrap();
    assert!(x_int != a);
    assert!(x_str != b);
    l_int.remove(0);
    l_str.remove(1);
}

