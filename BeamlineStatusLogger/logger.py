from collections import Iterable


def as_iterable(object):
    if isinstance(object, Iterable):
        return object
    else:
        return [object]


class Logger:
    def __init__(self, source, processors, sink, timer):
        self.source = source
        self.processors = as_iterable(processors)
        self.sink = sink
        self.timer = timer

    def run(self):
        while True:
            self.timer()
            data = self.source.read()
            for proc in self.processors:
                data = proc(data)
            self.sink.write(data)
