import asyncio
import logging
from enum import Enum
from logging import NullHandler
from platform import platform

from aiocorenlp.version import __version__

__all__ = [
    "__version__",
    "async_corenlp_server",
    "async_ner_server",
    "async_corenlp_socket",
    "logger",
    "EntityTypePair",
    "TagResult",
    "OutputFormat",
    "pos_tag",
    "ner_tag",
]


logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())

if platform() == "Windows":
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)


EntityTypePair = tuple[str, str]
TagResult = list[EntityTypePair]


class OutputFormat(Enum):
    """https://nlp.stanford.edu/software/crf-faq.shtml#j

    What options are available for formatting the output of the classifier?

    At the command line, there are five choices available for determining the output format of Stanford NER. You can
    choose an outputFormat of: xml, inlineXML, tsv, taggedEntities or slashTags (the default).

    XML formats preserve whitespace while the others do not.
    """
    SLASH_TAGS = "slashTags"
    XML = "xml"
    INLINE_XML = "inlineXML"
    TSV = "tsv"
    TAGGED_ENTITIES = "taggedEntities"


async def pos_tag(text: str | bytes, **kwargs):
    """Tag text using the Stanford POS tagger.

    :param text: Text to tag
    :param kwargs: See docstring of [AsyncPosServer]
    :return: List of tag tuples (entity_type, entity)
    """
    from aiocorenlp.async_pos_server import AsyncPosServer

    server: AsyncPosServer
    async with AsyncPosServer(**kwargs) as server:
        return await server.get_socket().tag(text)


async def ner_tag(text: str | bytes, **kwargs):
    """Tag text using the Stanford NER tagger.

    :param text: Text to tag
    :param kwargs: See docstring of [AsyncNerServer]
    :return: List of tag tuples (entity_type, entity)
    """
    from aiocorenlp.async_ner_server import AsyncNerServer

    server: AsyncNerServer
    async with AsyncNerServer(**kwargs) as server:
        return await server.get_socket().tag(text)
