from time import sleep, time


class SynchronizedPeriodicTimer:
    """
        Sleep until the end of a period

        If an instance with a period p is called (with an optional Boolean
        argument), it blocks until the system clock reaches the next multiple
        of p, e.g., if the period is 5 s and the time is 12:34:56 when called,
        the call will block until 12:35:00.

        Parameters
        ----------
        period : number
            The period in seconds
        offset : number, optional
            If given, the blocking duration is adjusted by offset % period
        p_max : number, optional
            If given and the instance is called `fail_tol` consecutive number
            of times with a False argument, the `period` will be doubled in
            each of following calls until period would exceed `p_max`. The
            period (and the internal fail_count) is reset to its initial value
            the next time a True argument is recieved
        fail_tol : number, optional
            Number of times the instance can be called with a False argument
            before the period is increased. Has an effect only if `p_max` is
            given

        Raises
        ------
        ValueError
            On construction if `p_max` is small than `period`
    """
    def __init__(self, period, offset=0, p_max=None, fail_tol=3):
        self.period = period
        self.offset = offset
        self.p_min = period
        if p_max is None:
            self.p_max = period
        elif p_max >= period:
            self.p_max = p_max
        else:
            raise ValueError("The period cannot be larger than the maximum" +
                             "value. Got period = ", + str(period) +
                             " and max = " + str(p_max))
        self.fail_tol = fail_tol
        self.fail_count = 0

    def __call__(self, success=True):
        if success:
            self.fail_count = 0
            self.period = self.p_min
            self._sleep()
        else:
            self.fail_count += 1
            if self.fail_count > self.fail_tol and self.period*2 <= self.p_max:
                self.period = self.period*2
            self._sleep()

    def _sleep(self):
        sleep(self.period - (time() - self.offset) % self.p_min)


def PeriodicTimer(period, p_max=None, fail_tol=3):
    """
        Sleep until the end of a period

        This is just a function returning a `SynchronizedPeriodicTimer`
        instance with an offset obtained from the system clock at construction
        time.

        Parameters
        ----------
        period : number
            The period in seconds
        p_max : number, optional
            If given and the instance is called `fail_tol` consecutive number
            of times with a False argument, the `period` will be doubled in
            each of following calls until period would exceed `p_max`. The
            period (and the internal fail_count) is reset to its initial value
            the next time a True argument is recieved
        fail_tol : number, optional
            Number of times the instance can be called with a False argument
            before the period is increased. Has an effect only if `p_max` is
            given

        Raises
        ------
        ValueError
            On construction if `p_max` is small than `period`
    """
    return SynchronizedPeriodicTimer(period, offset=time() % period,
                                     p_max=p_max, fail_tol=fail_tol)
