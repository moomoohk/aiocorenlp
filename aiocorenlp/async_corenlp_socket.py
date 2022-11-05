import re
from asyncio import open_connection, StreamReader, StreamWriter
from contextlib import asynccontextmanager
from typing import Iterable, cast

from aiocorenlp import OutputFormat, EntityTypePair, TagResult, logger

# Regex patterns for various tagging options for entity parsing
SLASHTAGS_EPATTERN = re.compile(r'(.+?)/([A-Z]+)?\s*')
XML_EPATTERN = re.compile(r'<wi num=".+?" entity="(.+?)">(.+?)</wi>')
INLINEXML_EPATTERN = re.compile(r'<([A-Z]+?)>(.+?)</\1>')
TSV_EPATTERN = re.compile(r'(.+?)\t(.+?)\r\n')


@asynccontextmanager
async def tcpip4_socket(host, port):
    reader, writer = await open_connection(host, port)
    try:
        yield reader, writer
    finally:
        writer.close()
        await writer.wait_closed()


class AsyncCorenlpSocket:
    def __init__(self, port: int, host="localhost", output_format: OutputFormat = OutputFormat.INLINE_XML):
        """
        :param port: Server port
        :param host: Server host
        :param output_format:
        """
        if isinstance(output_format, str):
            output_format = OutputFormat(output_format)

        if not isinstance(port, int):
            raise ValueError("Port must be an integer")

        self.host = host
        self.port = port
        self.output_format = output_format

    async def send_text(self, text: str | bytes):
        """Sends text to tag through the socket to the server.

        :param text: Text to send
        :return: Tagged text from received from server
        """
        if not isinstance(text, bytes):
            text = text.encode()

        for s in (b"\f", b"\n", b"\r", b"\t", b"\v"):  # Strip whitespaces
            text = text.replace(s, b'')

        text += b"\n"  # Ensure EOL

        reader: StreamReader
        writer: StreamWriter
        async with tcpip4_socket(self.host, self.port) as (reader, writer):
            writer.write(text)
            tagged_text = await reader.read(10 * len(text))

        return tagged_text.decode()

    async def tag(self, text: str) -> TagResult | None:
        """Return all the named entities in text as a list of tags.

        :param text: Text to tag
        :returns: List of tag tuples (entity_type, entity)
        """
        tagged_text = await self.send_text(text)

        match self.output_format:
            case OutputFormat.SLASH_TAGS:
                entities = self._slashTags_parse_entities(tagged_text)

            case OutputFormat.XML:
                entities = self._xml_parse_entities(tagged_text)

            case OutputFormat.TSV:
                entities = self._tsv_parse_entities(tagged_text)

            case OutputFormat.INLINE_XML:
                entities = self._inlineXML_parse_entities(tagged_text)

            case output_format:
                logger.error(f"Unrecognized output format: {output_format}")
                return None

        return list(entities)

    def _slashTags_parse_entities(self, tagged_text: str) -> Iterable[EntityTypePair]:
        """Return a list of token tuples (entity_type, token) parsed
        from slashTags-format tagged text.

        :param tagged_text: slashTag-format entity tagged text
        """
        return (cast(EntityTypePair, match.groups())[::-1] for match in SLASHTAGS_EPATTERN.finditer(tagged_text))

    def _xml_parse_entities(self, tagged_text) -> Iterable[EntityTypePair]:
        """Return a list of token tuples (entity_type, token) parsed
        from xml-format tagged text.

        :param tagged_text: xml-format entity tagged text
        """
        return (cast(EntityTypePair, match.groups()) for match in XML_EPATTERN.finditer(tagged_text))

    def _inlineXML_parse_entities(self, tagged_text) -> Iterable[EntityTypePair]:
        """Return a list of entity tuples (entity_type, entity) parsed
        from inlineXML-format tagged text.

        :param tagged_text: inlineXML-format tagged text
        """
        return (cast(EntityTypePair, match.groups()) for match in INLINEXML_EPATTERN.finditer(tagged_text))

    def _tsv_parse_entities(self, tagged_text) -> Iterable[EntityTypePair]:
        """Return a list of entity tuples (entity_type, entity) parsed
        from tsv-format tagged text.

        :param tagged_text: tsv-format tagged text
        """
        return (cast(EntityTypePair, match.groups())[::-1] for match in TSV_EPATTERN.finditer(tagged_text))
