from aiocorenlp.async_corenlp_server import AsyncCorenlpServer


class AsyncPosServer(AsyncCorenlpServer):
    @property
    def _cmd(self):
        return [
            "-cp", self.jar_path,
            "edu.stanford.nlp.tagger.maxent.MaxentTaggerServer",
            "-loadClassifier", self.model_path,
            "-outputFormat", self.output_format.value,
            "-tokenizerFactory", "edu.stanford.nlp.process.WhitespaceTokenizer",
            "-tokenizerOptions", '"tokenizeNLs=false"',
            "-encoding", self.encoding,
            "-port", str(self._actual_port),
        ]

    @property
    def _jar_name(self):
        return "stanford-postagger-withModel.jar"
