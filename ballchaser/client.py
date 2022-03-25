from typing import Dict

from requests import Session


class BallChaser:
    _bc_url = "https://ballchasing.com/api"

    def __init__(self, token: str):
        self.session = Session()
        self.session.headers["Authorization"] = token
        self.__set_patronage()

    def __set_patronage(self) -> None:
        """
        Determine and set patron level so that we know what rate limits to apply
        when hitting endpoints.
        """
        r = self.session.get(self._bc_url)
        if not r.status_code == 200:
            raise Exception(r.json()["error"])
        self.patronage = r.json()["type"]

    def get_maps(self) -> Dict:
        """
        Get dict of map codes to map names (map as in stadium).
        """
        response = self.session.get(f"{self._bc_url}/maps")
        if not response.status_code == 200:
            raise Exception(response.text)
        return response.json()
