# aiocorenlp

High-fidelity `asyncio` capable Stanford [CoreNLP](https://github.com/stanfordnlp/CoreNLP/) library.

Heavily based on [ner](https://github.com/dat/pyner) and [nltk](https://github.com/nltk/nltk).

## Rationale and differences from `nltk`
For every tag operation (in other words, every call to `StanfordTagger.tag*`), `nltk` runs a Stanford JAR (`stanford-ner.jar`/`stanford-postagger.jar`) in a newly spawned Java subprocess. 
In order to pass the input text to these JARs, `nltk` first writes it to a `tempfile` and includes its path in the Java command line using the `-textFile` flag.

This method works well in sequential applications, however once scaled up by concurrency and stress problems begin to arise:

1. Python's `tempfile.mkstemp` doesn't work very well on Windows to begin with and starts to break down under stress.
   * Calls to `tempfile.mkstemp` start to fail which in turn results in Stanford code failing (no input file to read).
   * Temporary files get leaked resulting in negative impact on disk usage.
2. Repeated calls to `subprocess` mean:
   * Multiple Java processes run in parallel causing negative impact on CPU and memory usage.
   * OS-level subprocess and Java startup code has to be run every time causing additional negative impact on CPU usage.

All this causes unnecessary slowdown and bad reliability to user-written code.

Patching `nltk`'s code to use `tempfile.TemporaryDirectory` instead of `tempfile.mkstemp` seemed to resolve issue 1 but issue 2 would require more work. 

This library runs the Stanford code in a server mode and sends input text over TCP, meaning:

1. Filesystem operations and temporary files/directories are avoided entirely.
2. There's no need to run a Java subprocess more than once.
3. The only synchronization bottleneck is offloaded to Java's `SocketServer` class which is used in the Stanford code.
4. CPU, memory and disk usage is greatly reduced.

### Differences from `ner`
* `asyncio` support.
* [Method name mangling](https://docs.python.org/3/tutorial/classes.html#private-variables) is inexplicably enabled in the [`ner.client.NER` class](https://https://github.com/dat/pyner/blob/master/ner/client.py), making subclassing not practical.
* The ner library appears to be abandoned.

## Basic Usage

```pycon
>>> from aiocorenlp import ner_tag
>>> await ner_tag("I complained to Microsoft about Bill Gates.")
[('O', 'I'), ('O', 'complained'), ('O', 'to'), ('ORGANIZATION', 'Microsoft'), ('O', 'about'), ('PERSON', 'Bill'), ('PERSON', 'Gates.')]
```

This usage doesn't require interfacing with the server and socket directly and is suitable for low frequency/one-time tagging.

## Advanced Usage

To fully take advantage of this library's benefits the `AsyncNerServer` and `AsyncPosServer` classes should be used:
```python
from aiocorenlp.async_ner_server import AsyncNerServer
from aiocorenlp.async_corenlp_socket import AsyncCorenlpSocket

server = AsyncNerServer()
port = server.start()
print(f"Server started on port {port}")

socket: AsyncCorenlpSocket = server.get_socket()

while True:
    text = input("> ")
    if text == "exit":
        break

    print(await socket.tag(text))

server.stop()
```

Context manager is supported as well: 
```python
from aiocorenlp.async_ner_server import AsyncNerServer

server: AsyncNerServer
async with AsyncNerServer() as server:
    socket = server.get_socket()
    
    while True:
        text = input("> ")
        if text == "exit":
            break
    
        print(await socket.tag(text))
```

## Configuration

As seen above, all classes and functions this library exposes may be used without arguments (default values).

Optionally, the following arguments may be passed to `AsyncNerServer` (and by extension `ner_tag`/`pos_tag`):

* `port`: Server bind port. Leave `None` for random port.
* `model_path`: Path to language model. Leave `None` to let `nltk` find the model (supports `STANFORD_MODELS` environment variable).
* `jar_path`: Path to `stanford-*.jar`. Leave `None` to let `nltk` find the jar (supports `STANFORD_POSTAGGER` environment variable, for NER as well).
* `output_format`: Output format. See `OutputFormat` enum for values. Default is `slashTags`. 
* `encoding`: Output encoding.
* `java_options`: Additional JVM options.

It is not possible to configure the server bind interface. This is a limitation imposed by the Stanford code.
