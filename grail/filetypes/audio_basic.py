"""audio/basic MIME type handler"""

class parse_audio_basic:

    def __init__(self, viewer, reload=False):
        viewer.send_flowing_data("(Listen to the audio!)\n")
        import ossaudiodev
        self.device = p = ossaudiodev.open("w")
        
        # strict=True not accepted as keyword argument
        p.setparameters(ossaudiodev.AFMT_MU_LAW, 1, 8000, True)

    def feed(self, buf):
        self.device.write(bytes(buf))  # Requires an immutable buffer

    def close(self):
        self.device.close()
