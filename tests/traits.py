# """
# Examples of classes that derive from other classes. These could
# use abstract base classes to enforce the implementation of methods
# in derived classes, but that is not essential to the pattern.
# """

class Waddle:
    def waddle(self, elegant: bool):
        # """
        # Waddle like a duck, either elegantly or not.
        # """
        pass

    def run(self, speed: int):
        # """
        # Ducks can also run
        # """
        pass

class Quack:
    def quack(self, volume: float):
        # """
        # Quack like a duck
        # """
        pass

    def echoes(self) -> bool:
        # """
        # Does this quack echo?
        # """
        pass

class Duck(Waddle, Quack):
    def __init__(self, echoes: bool):
        self._echoes = echoes

    def waddle(self, elegant: bool):
        if elegant:
            print("elegantly ", end='')
        print("waddle")

    def run(self, speed: int):
        print("run", speed)

    def quack(self, volume: float):
        print("quack", volume)

    def echoes(self) -> bool:
        return self._echoes

    def fly(self):
        print("fly")

def make_it_waddle(waddler: Waddle):
    waddler.waddle(False)

def make_it_quack(quacker: Quack):
    quacker.quack(10.0)

def tests():
    donald = Duck(True)
    make_it_waddle(donald)
    make_it_quack(donald)
