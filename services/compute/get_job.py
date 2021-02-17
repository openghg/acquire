from Acquire.Compute import Cluster

from typing import Dict


def run(args: Dict) -> Dict:
    """This function gets the job with the specified UID in the specified
    state, optionally changing it to a new state

    Args:
        args: Dictionary containing job run data
    Returns:
        dict: Dictionary holding encrypted job data
    """
    uid = str(args["uid"])
    passphrase = str(args["passphrase"])
    start_state = str(args["start_state"])

    try:
        end_state = str(args["end_state"])
    except KeyError:
        end_state = None

    cluster = Cluster.get_cluster()

    job = cluster.get_job(uid=uid, passphrase=passphrase, start_state=start_state, end_state=end_state)

    return {"job": cluster.encrypt_data(job.to_data())}
