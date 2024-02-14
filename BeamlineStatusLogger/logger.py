from collections.abc import Iterable


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
        self.timer.reset()
        success = True
        while self.timer(success):
            data = self.source.read()
            for proc in self.processors:
                data = proc(data)
            success = self.sink.write(data)

    def abort(self):
        self.timer.abort()
