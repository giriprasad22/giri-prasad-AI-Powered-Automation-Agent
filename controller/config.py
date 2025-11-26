import os
from dotenv import load_dotenv
from ollama import Client


class Config:
    """
    Configuration class for managing settings.

    Attributes:
        verbose (bool): Flag indicating whether verbose mode is enabled.
        ollama_host (str): URL to ollama running remotely.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            # Put any initialization here
        return cls._instance

    def __init__(self):
        load_dotenv()
        self.verbose = False
        self.ollama_host = None  # instance variables are backups in case saving to a `.env` fails

    def initialize_ollama(self):
        if self.ollama_host:
            if self.verbose:
                print("[Config][initialize_ollama] using cached ollama host")
        else:
            if self.verbose:
                print(
                    "[Config][initialize_ollama] no cached ollama host. Assuming ollama running locally."
                )
            self.ollama_host = os.getenv("OLLAMA_HOST", None)
        model = Client(host=self.ollama_host)
        return model
