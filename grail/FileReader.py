"""File reader class -- read from a URL to a file in the background."""

from .BaseReader import BaseReader
from .grailutil import close_subprocess

class FileReader(BaseReader):

    """File reader class -- read from a URL to a file in the background.

    Derived classes are supposed to override handle_error() and
    handle_done() to specify what should happen next, and possibly
    handle_meta() to decide whether to continue based on the data
    type.

    The methods handle_data() and handle_eof() are implemented at this
    level and should normally be left alone (or extended, not
    overridden).

    """

    def __init__(self, context, api, filename):
        self.filename = filename
        self.fp = None
        BaseReader.__init__(self, context, api)

    def handle_data(self, data):
        try:
            if self.fp is None:
                self.fp = self.open_file()
            self.fp.write(data)
        except EnvironmentError as msg:
            self.stop()
            self.handle_error(-1, "EnvironmentError", {'detail': msg})
            return
 
    def open_file(self):
        return open(self.filename, "wb")

    def handle_eof(self):
        if self.fp:
            self.fp.close()
        self.handle_done()

    def handle_done(self):
        pass


class TempFileReader(FileReader):

    """Derived class of FileReader that chooses a temporary file.

    This also supports inserting a filtering pipeline.
    """

    def __init__(self, context, api):
        self.pipeline = None
        self.proc = None
        import tempfile
        import os
        tf = tempfile.NamedTemporaryFile("wb", delete=False)
        try:
            FileReader.__init__(self, context, api, tf.name)
            self.tf = tf
        except:
            tf.close()
            os.unlink(tf.name)
            raise
    
    def stop(self):
        self.tf.close()
        return FileReader.stop(self)

    def set_pipeline(self, pipeline):
        """New method to select the filter pipeline."""
        self.pipeline = pipeline

    def getfilename(self):
        """New method to return the file name chosen."""
        return self.tf.name

    def open_file(self):
        if not self.pipeline:
            return self.tf
        else:
            import subprocess
            self.proc = subprocess.Popen(self.pipeline, shell=True,
                stdin=subprocess.PIPE, stdout=self.tf, bufsize=-1)
            self.tf.close()
            return self.proc.stdin
    
    def handle_eof(self):
        if self.proc:
            close_subprocess(self.proc)
        return FileReader.handle_eof(self)
