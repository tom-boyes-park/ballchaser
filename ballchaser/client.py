from requests import Session


class BallChaser:
    _bc_url = "https://ballchasing.com/api/"

    def __init__(self, token: str):
        self.session = Session()
        self.session.headers["Authorization"] = token
        self.__set_patronage()

    def __set_patronage(self):
        """
        Determine and set patron level so that we know what rate limits to apply
        when hitting endpoints.
        """
        r = self.session.get(self._bc_url)
        if not r.status_code == 200:
            raise Exception(r.json()["error"])
        self.patronage = r.json()["type"]
