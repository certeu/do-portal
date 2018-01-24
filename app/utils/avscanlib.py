import os
import sys
import subprocess
import configparser
import logging
import re
import shlex

logging.getLogger(__name__).addHandler(logging.NullHandler())

try:
    import pyclamd
except ImportError as ie:
    logging.error(ie.message)


def popen(*args, **kwargs):
    defaults = {
        'stdout': subprocess.PIPE,
        'stderr': subprocess.PIPE,
        'stdin': subprocess.PIPE
    }
    defaults.update(kwargs)
    return subprocess.Popen(args, **defaults)


class Antivirus:
    def __init__(self, *args, **kwargs):
        self._results = {}
        self.result_regex = None
        self.result_key = 0
        self.result_val = 1
        for k in kwargs:
            setattr(self, k, kwargs[k])

    def build(self, path):
        return shlex.split(self.path + ' ' + self.args + ' ' + path)

    def exec(self, cmd):
        out = None
        with popen(*cmd) as scan_proc:
            stdout, stderr = scan_proc.communicate()
            out = stdout.decode('utf-8').strip()
            if scan_proc.returncode != 0:
                logging.error(stderr)
        return out

    def scan(self, path):
        cmd = self.build(path)
        cmd_result = self.exec(cmd)
        matches = re.findall(self.result_regex, cmd_result,
                             re.IGNORECASE | re.MULTILINE)
        for m in matches:
            self._results[m[self.result_key]] = m[self.result_val]
        return self._results

    def __repr__(self):
        kws = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        args_ = []
        for k, v in kws.items():
            args_.append('{!s}={!r}'.format(k, v))

        return '{}.{}({})'.format(self.__class__.__module__,
                                  self.__class__.__qualname__,
                                  ', '.join(args_))


class ClamAV(Antivirus):
    def scan(self, path):
        cs = pyclamd.ClamdUnixSocket(filename=self.socket)
        try:
            result_ = cs.scan_file(path)
            if result_:
                self._results.update(result_)
        except Exception as e:
            logging.error(e)

        return self._results


class ESET(Antivirus):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        self.result_regex = 'name="(.*)", threat="(.*)",'

    def scan(self, path):
        cmd = self.build(path)
        result = self.exec(cmd)
        matches = re.findall(self.result_regex, result,
                             re.IGNORECASE | re.MULTILINE)
        for m in matches:
            m_ = m[1][:m[1].find('", ')]
            if m_ != '':
                self._results[m[0]] = m[1][:m[1].find('", ')]
        return self._results


class WindowsDefender(Antivirus):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        self.result_regex = 'Threat (.*) identified\.'

    def exec(self, cmd):
        out = None
        with popen(*cmd) as scan_proc:
            stdout, stderr = scan_proc.communicate()
            out = stderr.decode('utf-8').strip()
            if scan_proc.returncode != 0:
                logging.error(stderr)
        return out

    def scan(self, path):
        os.chdir(os.path.dirname(self.path))
        cmd = self.build(path)
        result = self.exec(cmd)
        matches = re.findall(self.result_regex, result,
                             re.IGNORECASE | re.MULTILINE)
        for m in matches:
            self._results[path] = m
        return self._results


class FProt(Antivirus):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        self.result_regex = "\<(.*)\>\s+(.*)"
        self.result_key = 1
        self.result_val = 0


class FSecure(Antivirus):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        self.result_regex = "(.*): Infected: (.*) \[[a-z]+\]"


class SAVAPI(Antivirus):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        self.result_regex = "([0-9]{3}) (.*)<<<(.*);(.*);(.*)"
        self.result_key = 1
        self.result_val = 2


class DrWeb(Antivirus):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        self.result_regex = "\>{0,1}(.*) infected with (.*)"


class Scanner:
    """Helper class to start available AVs
    """

    def __init__(self, config):
        self.config_file = config
        self.config = None
        self.engines = []
        self.load_config(config)

    def load_config(self, filename):
        """Load configuration from filename.

        :param filename: Absolute PATH to configuration file
        """
        if not os.path.exists(filename):
            fmt = 'No such file: {}'
            raise FileNotFoundError(fmt.format(filename))
        cp = configparser.ConfigParser()
        cp.optionxform = str
        cp.read(filename)
        self.engines = list(cp.sections())
        self.config = cp

    def scan(self, path):
        avlib_ = sys.modules[__name__]
        results = {}
        for avname in self.config.sections():
            avkwds = dict(self.config[avname].items())
            try:
                avcls_ = getattr(avlib_, avname.replace('-', ''))
                av = avcls_(**avkwds)
                results[avname] = av.scan(path)
            except AttributeError as ae:
                logging.warn(ae)

        return results

    def __repr__(self):
        fmt = "{}(config='{}')"
        return fmt.format(self.__class__.__name__, self.config_file)
