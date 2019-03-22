
from Acquire.Service import create_return_value

from Acquire.Identity import Authorisation

from Acquire.Storage import UserDrives, DriveInfo


def run(args):
    """Call this function to open and return a handle to the
       user's requested CloudDrive. This will create the
       drive (and the all intermediate drives) unless the
       user sets autocreate to false
    """

    authorisation = Authorisation.from_data(args["authorisation"])
    name = args["name"]

    try:
        autocreate = args["autocreate"]

        if autocreate is False:
            autocreate = False
        else:
            autocreate = True
    except:
        autocreate = True

    drives = UserDrives(authorisation=authorisation)

    drive = drives.get_drive(name=name, autocreate=autocreate)

    return_value = create_return_value()

    return_value["drive"] = drive.to_data()

    return return_value
