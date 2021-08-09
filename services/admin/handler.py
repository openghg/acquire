import sys
import os
import subprocess


def _one_hot_spare():
    """This function will (in the background) cause the function service
    to spin up another hot spare ready to process another request.
    This ensures that, if a user makes a request while this
    thread is busy, then the cold-start time to spin up another
    thread has been mitigated.

    Args:
         None
     Returns:
         None

    """
    devnull = open(os.devnull, "w")
    subprocess.Popen(
        ["nohup", sys.executable, "one_hot_spare.py"],
        stdout=devnull,
        stderr=subprocess.STDOUT,
    )
