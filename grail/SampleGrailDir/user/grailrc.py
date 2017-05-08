# Grail initialization file

# Turn on remote control.  Ignore error that gets raised if some
# other Grail is being remote controlled.
from grail import RemoteControl
RemoteControl.register_loads()
try:
    RemoteControl.start()
except RemoteControl.ClashError:
    pass
