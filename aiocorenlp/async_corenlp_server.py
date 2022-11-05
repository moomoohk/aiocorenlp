from abc import ABC, abstractmethod
from asyncio import create_subprocess_exec
from asyncio.subprocess import Process
from subprocess import PIPE
from contextlib import contextmanager
from os import PathLike
from socket import socket

from nltk.internals import find_jar, find_file, find_binary

from aiocorenlp import OutputFormat, logger
from aiocorenlp.async_corenlp_socket import AsyncCorenlpSocket


class AsyncCorenlpServer(ABC):
    DEFAULT_MODEL_NAME = "english.all.3class.distsim.crf.ser.gz"

    def __init__(
            self,
            port: int = None,
            model_path: str | PathLike = None,
            jar_path: str | PathLike = None,
            output_format: OutputFormat = OutputFormat.SLASH_TAGS,
            encoding: str = "utf-8",
            java_options: str | list[str] = "-mx1000m",
    ):
        """Stanford CoreNLP server runner

        :param port: Server bind port. Leave None for random port
        :param model_path: Path to language model
        :param jar_path: Path to stanford-ner.jar
        :param output_format: Output format
        :param encoding: Output encoding
        :param java_options: Additional JVM options
        """
        self.port = port
        self.jar_path = jar_path
        self.model_path = model_path
        self.output_format = output_format
        self.encoding = encoding
        self.java_options = java_options

        self._process: Process | None = None
        self._actual_port: int | None = None

        if self.jar_path is None:
            self.jar_path = find_jar(
                self._jar_name,
                env_vars=("STANFORD_POSTAGGER",),
                searchpath=(),
            )

        if self.model_path is None:
            self.model_path = find_file(
                self.DEFAULT_MODEL_NAME, env_vars=("STANFORD_MODELS",)
            )

    @property
    @abstractmethod
    def _cmd(self):
        pass

    @property
    @abstractmethod
    def _jar_name(self):
        pass

    @staticmethod
    @contextmanager
    def _reserve_port(port: int):
        s = socket()

        # If provided port is None, reserve random port from OS
        s.bind(("", port or 0))
        reserved_port: int = s.getsockname()[1]
        yield reserved_port

        s.close()

    async def start(self) -> tuple[str, int]:
        """Start server

        :return: Tuple of bound host (127.0.0.1) and port number
        """
        # Hacked together from nltk code
        if self._process is not None:
            raise Exception(f"Server is already running on port {self._actual_port}")

        # If needed, reserve random port from OS and release it right before running
        with self._reserve_port(self.port) as self._actual_port:
            logger.debug(f"Starting NER server on port {self._actual_port}")

            java_options = self.java_options or ""
            if isinstance(java_options, str):
                java_options = java_options.split()

            java_options = list(java_options)

            args = java_options + self._cmd

            java_bin = find_binary(
                "java",
                env_vars=["JAVAHOME", "JAVA_HOME"],
                binary_names=["java.exe"],
            )

            logger.debug(f"{java_bin} {args}")

        self._process = await create_subprocess_exec(java_bin, *args, stdout=PIPE, stderr=PIPE, stdin=PIPE)

        return "127.0.0.1", self._actual_port

    async def stop(self):
        """Stop server"""
        if self._process is not None and not self._process.returncode:
            self._process.terminate()

        self._process = None
        self._actual_port = None

    def get_socket(self):
        if self._process is None:
            return None

        return AsyncCorenlpSocket(self._actual_port, "127.0.0.1", self.output_format)

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

