pub struct Foo {
    pub a: i64,
    pub b: String,
    pub counter: i64,
}

impl Foo {
    pub fn new(a: i64, b: &str) -> Foo {
        let tmp_a = a;
        let tmp_b = b.to_string();
        let tmp_counter = 0;
        Foo {
            a: tmp_a,
            b: tmp_b,
            counter: tmp_counter,
        }
    }

    pub fn increment(&mut self) {
        self.counter += 1;
    }

    pub fn add(&mut self, x: i64) {
        self.counter += x;
    }

}

pub fn create_foo(a: i64, b: &str) -> Foo {
    let foo = Foo::new(a, b);
    return foo;
}

pub fn increment_foo(foo: &mut Foo) {
    let was = foo.counter;
    foo.increment();
    let now = foo.counter;
    assert!(now == was + 1);
}

pub fn add_foo(foo: &mut Foo, x: i64) {
    let was = foo.counter;
    foo.add(x);
    let now = foo.counter;
    assert!(now == was + x);
}

pub fn examine_foo(foo: &Foo) {
    let b = foo.b.to_string();
    let a = foo.a;
    println!("{} {} {} {}", "a = ", a, "b = ", b);
}

