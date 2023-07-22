import json
import math
import os
import time
from http import HTTPStatus

import requests
from bs4 import BeautifulSoup
from loguru import logger


class ColorCanvas:
    def __init__(self) -> None:
        self.red = None
        self.read_file()

    def read_file(self, canvas_path="red.json"):
        canvas_full_path = os.path.join(os.getcwd(), canvas_path)
        f = open(canvas_full_path)
        self.red = json.load(f)
        f.close()

    def print(self):
        print(self.red)


class PlaceClient:
    def __init__(self, canvas):
        self.access_token = None
        self.access_token_expires_at_timestamp = None
        self.canvas = canvas
        self.credentials = []
        self.logger = logger
        self.get_credentials()

    def get_credentials(self):
        credentials_path = os.path.join(os.getcwd(), "credentials.json")
        f = open(credentials_path)
        self.credentials = json.load(f)
        f.close()
        logger.info(f"got credentials for {len(self.credentials)} users")

    def set_token(self, credentials: dict):
        try:
            username = credentials.get("username")
            password = credentials.get("password")
        except Exception:
            logger.error(
                "You need to provide all required fields to worker '{}'",
            )
            exit(1)

        while True:
            try:
                client = requests.Session()
                # client.proxies = proxy.get_random_proxy(self, name)
                client.headers.update(
                    {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36",
                        "content-type": "application/x-www-form-urlencoded",
                    }
                )

                r = client.get(
                    "https://www.reddit.com/login",
                    # proxies=proxy.get_random_proxy(self, name),
                )
                login_get_soup = BeautifulSoup(r.content, "html.parser")
                csrf_token = login_get_soup.find("input", {"name": "csrf_token"})[
                    "value"
                ]
                data = {
                    "username": username,
                    "password": password,
                    "dest": "https://reddit.com/",
                    "csrf_token": csrf_token,
                }

                r = client.post(
                    "https://www.reddit.com/login",
                    data=data,
                    # proxies=proxy.get_random_proxy(self, name),
                )
                break
            except Exception:
                logger.error(
                    "Failed to connect to websocket, trying again in 30 seconds..."
                )
                time.sleep(30)

        if r.status_code != HTTPStatus.OK.value:
            # password is probably invalid
            logger.error("{} - Authorization failed!", username, password)
            logger.error("response: {} - {}", r.status_code, r.text)
            return
        else:
            logger.info("{} - Authorization successful!", username)
        logger.info("Obtaining access token...")
        r = client.get(
            "https://new.reddit.com/",
            # proxies=proxy.get_random_proxy(self, name),
        )
        data_str = (
            BeautifulSoup(r.content, features="html.parser")
            .find("script", {"id": "data"})
            .contents[0][len("window.__r = ") : -1]
        )
        data = json.loads(data_str)
        response_data = data["user"]["session"]

        if "error" in response_data:
            logger.error(
                "An error occured. Make sure you have the correct credentials. Response data: {}",
                response_data,
            )
            exit(1)

        self.access_token = response_data["accessToken"]
        # access_token_type = data["user"]["session"]["accessToken"]  # this is just "bearer"
        access_token_expires_in_seconds = response_data["expiresIn"]
        self.access_token_expires_at_timestamp = (
            math.floor(time.time()) + access_token_expires_in_seconds
        )

    def set_pixel(self, x, y, canvas_index, color):
        payload = json.dumps(
            {
                "operationName": "setPixel",
                "variables": {
                    "input": {
                        "actionName": "r/replace:set_pixel",
                        "PixelMessageData": {
                            "coordinate": {"x": x, "y": y},
                            "colorIndex": color,
                            "canvasIndex": canvas_index,
                        },
                    }
                },
                "query": "mutation setPixel($input: ActInput!) {\n  act(input: $input) {\n    data {\n      ... on BasicMessage {\n        id\n        data {\n          ... on GetUserCooldownResponseMessageData {\n            nextAvailablePixelTimestamp\n            __typename\n          }\n          ... on SetPixelResponseMessageData {\n            timestamp\n            __typename\n          }\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n",
            }
        )
        headers = {
            "origin": "https://garlic-bread.reddit.com",
            "referer": "https://garlic-bread.reddit.com/",
            "apollographql-client-name": "garlic-bread",
            "Authorization": "Bearer " + self.access_token,
            "Content-Type": "application/json",
        }
        response = requests.request(
            "POST",
            "https://gql-realtime-2.reddit.com/query",
            headers=headers,
            data=payload,
        )
        logger.info(
            "Setting pixel x:{}, y:{}, canvas:{}, color:{}", x, y, canvas_index, color
        )

    def defend(self):
        if len(self.canvas.red) == 0:
            self.canvas.read_file()
        for credentials in self.credentials:
            self.set_token(credentials)
            if not self.access_token:
                logger.info("Login for {} failed",credentials)
                logger.info("Skipping ...")
                continue
            tile = self.canvas.red.pop(0)
            self.set_pixel(
                tile.get("x"), tile.get("y"), tile.get("canvas"), tile.get("color")
            )
            logger.info("**" * 20)
        logger.info("Durmiendo 5 minutos")
        time.sleep(5 * 60)


if __name__ == "__main__":
    canvas = ColorCanvas()
    place_client = PlaceClient(canvas)
    place_client.defend()
