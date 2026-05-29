from ria_z_ble_car import PaiZCar


TEAM_ID = 7


car = PaiZCar(TEAM_ID)
car.connect()


while True:
    car.command("F", 800)
    car.command("S", 200)

    car.command("L", 800)
    car.command("S", 200)

    car.command("R", 800)
    car.command("S", 200)
