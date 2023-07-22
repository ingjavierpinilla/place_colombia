import json


def generate_red():
    l = []
    for i in range(808, 903):  # los marroquies tienen de la 808 a la 903
        # 23: rojo claro
        # 2: rojo
        color = 23 if i % 2 == 0 else 2
        tile = {"x": i, "y": 121, "canvas": 4, "color": color}
        l.append(tile)
    with open("red.json", "w") as json_file:
        json.dump(l, json_file)
