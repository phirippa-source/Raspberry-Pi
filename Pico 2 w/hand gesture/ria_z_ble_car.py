from ria_z_ble_car import PaiZCar


TEAM_ID = 7


car = PaiZCar(TEAM_ID)
car.connect()


while True:
    car.command("F", 300)
    car.command("S", 200)

    car.command("L", 300)
    car.command("S", 200)

    car.command("R", 300)
    car.command("S", 200)
