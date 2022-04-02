"""
Solution to the one-way tunnel
"""
import time
import random
from multiprocessing import Lock, Condition, Process
from multiprocessing import Value

SOUTH = "south"
NORTH = "north"

NCARS = 100
M = 5

# Monitor normal: entran coches en una dirección y los que van en dirección 
# contraria no pueden entrar hasta que no haya nadie en el túnel
class Monitor():
    def __init__(self):
        self.mutex = Lock()
        self.cars_north = Value('i',0)
        self.cars_south = Value('i',0)
        self.no_cars_north = Condition(self.mutex)
        self.no_cars_south = Condition(self.mutex)
    
    def arent_cars_south(self):
        return self.cars_south.value == 0
    
    def arent_cars_north(self):
        return self.cars_north.value == 0
    
    def wants_enter(self, direction):
        self.mutex.acquire()
        if direction == NORTH:
            self.no_cars_south.wait_for(self.arent_cars_south)
            self.cars_north.value += 1
        if direction == SOUTH:
            self.no_cars_north.wait_for(self.arent_cars_north)
            self.cars_south.value += 1
        self.mutex.release()

    def leaves_tunnel(self, direction):
        self.mutex.acquire()
        if direction == NORTH:
            self.cars_north.value -= 1
            self.no_cars_north.notify_all()
        if direction == SOUTH:
            self.cars_south.value -= 1
            self.no_cars_south.notify_all()
        self.mutex.release()
        
        
# Monitor evita_atascos: solo permitimos entrar un número máximo M de coches
# seguidos en una misma dirección 
class AntijamMonitor():
    def __init__(self):
        self.mutex = Lock()
        self.M = M
        self.cars_north = Value('i',0)
        self.cars_north_de_seguido = Value('i',0)
        self.cars_south = Value('i',0)
        self.cars_south_de_seguido = Value('i',0)
        self.no_cars_north = Condition(self.mutex)
        self.no_cars_south = Condition(self.mutex)
        self.no_hay_muchos_south_cond = Condition(self.mutex)
        self.no_hay_muchos_north_cond = Condition(self.mutex)

    def arent_cars_south(self):
        return self.cars_south.value == 0
    
    def no_hay_muchos_north(self):
        return self.cars_north_de_seguido.value < self.M
    
    def no_hay_muchos_south(self):
        return self.cars_south_de_seguido.value < self.M
    
    def arent_cars_north(self):
        return self.cars_north.value == 0
    
    def wants_enter(self, direction):
        self.mutex.acquire()
        if direction == NORTH:
            self.no_hay_muchos_north_cond.wait_for(self.no_hay_muchos_north)
            self.no_cars_south.wait_for(self.arent_cars_south)
            self.cars_north.value += 1
            self.cars_north_de_seguido.value += 1
            self.cars_south_de_seguido.value = 0
            self.no_hay_muchos_south_cond.notify_all()
        if direction==SOUTH:
            self.no_hay_muchos_south_cond.wait_for(self.no_hay_muchos_south)
            self.no_cars_north.wait_for(self.arent_cars_north)
            self.cars_south.value += 1
            self.cars_south_de_seguido.value += 1
            self.cars_north_de_seguido.value = 0
            self.no_hay_muchos_north_cond.notify_all()
        self.mutex.release()

    def leaves_tunnel(self, direction):
        self.mutex.acquire()
        if direction == NORTH:
            self.cars_north.value -= 1
            self.no_cars_north.notify_all()
        if direction == SOUTH:
            self.cars_south.value -= 1
            self.no_cars_south.notify_all()
        self.mutex.release()

#Monitor anti_atascos con coches esperando: si tenemos en cuenta que puede haber 
# más probabilidad de que se generen coches en una dirección que en otra, puede 
# darse el caso de que aunque hayan pasado ya los M coches seguidos, aun no haya
# coches esperando para entrar de la otra dirección, si esto ocurre pues también 
# se les permitirá pasar superando los M coches hasta que en el otro alguien quiera entrar
class WaitingAntijamMonitor():
    def __init__(self):
        self.mutex = Lock()
        self.M = M
        self.cars_north = Value('i',0)
        self.cars_north_waiting = Value('i',0)
        self.cars_north_deseguido = Value('i',0)
        self.cars_south = Value('i',0)
        self.cars_south_waiting = Value('i',0)
        self.cars_south_deseguido = Value('i',0)
        self.no_cars_north = Condition(self.mutex)
        self.no_cars_south = Condition(self.mutex)
        self.no_hay_muchos_south_cond = Condition(self.mutex)
        self.no_hay_muchos_north_cond = Condition(self.mutex)

    def arent_cars_south(self):
        return self.cars_south.value == 0
    
    def no_hay_muchos_north(self):
        return self.cars_north_deseguido.value < self.M or self.cars_south_waiting.value == 0
    
    def no_hay_muchos_south(self):
        return self.cars_south_deseguido.value < self.M or self.cars_north_waiting.value == 0
    
    def arent_cars_north(self):
        return self.cars_north.value == 0
    
    def wants_enter(self, direction):
        self.mutex.acquire()
        if direction == NORTH:
            self.cars_north_waiting.value += 1
            self.no_hay_muchos_north_cond.wait_for(self.no_hay_muchos_north)
            self.no_cars_south.wait_for(self.arent_cars_south)
            self.cars_north_waiting.value -= 1
            self.cars_north.value += 1
            self.cars_north_deseguido.value += 1
            self.cars_south_deseguido.value = 0
            self.no_hay_muchos_north_cond.notify_all()
            self.no_hay_muchos_south_cond.notify_all()
        if direction == SOUTH:
            self.cars_south_waiting.value += 1
            self.no_hay_muchos_south_cond.wait_for(self.no_hay_muchos_south)
            self.no_cars_north.wait_for(self.arent_cars_north)
            self.cars_south_waiting.value -= 1
            self.cars_south.value += 1
            self.cars_south_deseguido.value += 1
            self.cars_north_deseguido.value = 0
            self.no_hay_muchos_south_cond.notify_all()
            self.no_hay_muchos_north_cond.notify_all()
        self.mutex.release()

    def leaves_tunnel(self, direction):
        self.mutex.acquire()
        if direction == NORTH:
            self.cars_north.value -= 1
            self.no_cars_north.notify_all()
        if direction == SOUTH:
            self.cars_south.value -= 1
            self.no_cars_south.notify_all()
        self.mutex.release()




#Monitor tramposo: el sur hace trampas, y no podrá salir del túnel a no ser que
# haya dentro otros coches en direccion sur o que ya no haya coches esperando 
# para entrar en la dirección sur
class CheatMonitor():
    def __init__(self):
        self.mutex = Lock()
        self.cars_north = Value('i',0)
        self.cars_south = Value('i',0)
        self.cars_south_waiting = Value('i',0)
        self.no_cars_north = Condition(self.mutex)
        self.no_cars_south = Condition(self.mutex)
        self.leave_south = Condition(self.mutex)
        
    def arent_cars_south(self):
        return self.cars_south.value == 0
    
    def cheating_south(self):
        return self.cars_south.value > 1 or self.cars_south_waiting.value == 0
    
    def arent_cars_north(self):
        return self.cars_north.value == 0
    
    def wants_enter(self, direction):
        self.mutex.acquire()
        if direction == NORTH:
            self.no_cars_south.wait_for(self.arent_cars_south)
            self.cars_north.value += 1
        if direction == SOUTH:
            self.cars_south_waiting.value += 1
            self.no_cars_north.wait_for(self.arent_cars_north)
            self.cars_south.value += 1
            self.cars_south_waiting.value -= 1
            self.leave_south.notify_all()
        self.mutex.release()

    def leaves_tunnel(self, direction):
        self.mutex.acquire()
        if direction == NORTH:
            self.cars_north.value -= 1
            self.no_cars_north.notify_all()
        if direction == SOUTH:
            self.leave_south.wait_for(self.cheating_south)
            self.cars_south.value -= 1
            self.no_cars_south.notify_all()
        self.mutex.release()
        


   
def delay(n=3):
    time.sleep(random.random()*n)

def car(cid, direction, monitor):
    print(f"car {cid} direction {direction} created")
    delay(6)
    print(f"car {cid} heading {direction} wants to enter")
    monitor.wants_enter(direction)
    print(f"car {cid} heading {direction} enters the tunnel")
    delay(3)
    print(f"car {cid} heading {direction} leaving the tunnel")
    monitor.leaves_tunnel(direction)
    print(f"car {cid} heading {direction} out of the tunnel")



def main():
    monitor = Monitor()
    cid = 0
    for _ in range(NCARS):
        direction = NORTH if (random.randint(0,1))==1  else SOUTH
        cid += 1
        p = Process(target=car, args=(cid, direction, monitor))
        p.start()
        time.sleep(random.expovariate(1/0.5)) # a new car enters each 0.5s
    
if __name__=='__main__':
    main()