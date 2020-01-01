trait Waddle {
    fn waddle(&self, elegant: bool);
    fn run(&self, speed: i64);
}

trait Quack {
    fn quack(&self, volume: f64);
    fn echoes(&self) -> bool;
}

pub struct Duck {
    pub _echoes: bool,
}

impl Duck {
    pub fn new(echoes: bool) -> Duck {
        let tmp__echoes = echoes;
        Duck {
            _echoes: tmp__echoes,
        }
    }

    pub fn fly(&self) {
        println!("fly");
    }

}

impl Waddle for Duck {
    fn waddle(&self, elegant: bool) {
        if elegant {
            print!("elegantly ");
        }
        println!("waddle");
    }

    fn run(&self, speed: i64) {
        println!("{} {}", "run", speed);
    }

}

impl Quack for Duck {
    fn quack(&self, volume: f64) {
        println!("{} {}", "quack", volume);
    }

    fn echoes(&self) -> bool {
        return self._echoes;
    }

}

pub fn make_it_waddle(waddler: &mut Waddle) {
    waddler.waddle(false);
}

pub fn make_it_quack(quacker: &mut Quack) {
    quacker.quack(10.0);
}

pub fn tests() {
    let donald = Duck::new(true);
    make_it_waddle(donald);
    make_it_quack(donald);
}

