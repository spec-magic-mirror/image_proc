from flask import Flask, request, make_response
import sys, base64
from mole_detector import MoleDetector
import json
from mole_db_api import MoleDB
import os
import datetime
from Calibrate import Mole_Tracker
from pprint import pprint

middleware = Flask(__name__)
db = MoleDB()


@middleware.route("/", methods=["GET", "POST"])
def root():
    return 0

@middleware.route("/get_test", methods=["GET"])
def get_test():
    return "Hello from the Mole Detector!\n"

@middleware.route("/detect_moles", methods=["POST"])
def upload_image():
    error = {"error": ""}
    print "Got a request to detect moles"
    #TODO: add support for multiple users
    user_firstname = "Mani"
    user_lastname = "Moles"
    user_id, db_error = db.find_user_id(user_firstname, user_lastname)
    if db_error:
        error["error"] = db_error
        return json.dumps(error)

    timestamp = datetime.datetime.now()
    version = MoleDetector.version

    images = {"userId": user_id, "date": timestamp, "version": version, "images": {}}
    all_moles = {"date": timestamp, "images_id": "", "moles": []}

    all_images = request.files

    if len(all_images) == 0:
        error["error"] = "Didn't receive any images"
        print error["error"]
        return json.dumps(error)

    for orientation, image_storage in all_images.iteritems():
        filename = image_storage.filename
        #filename = type
        image = image_storage.read()
        #print filename

        with open(filename, 'w') as image_file:
            image_file.write(base64.b64decode(image))

        md = MoleDetector(filename)
        os.remove(filename)
        moles_file, moles_keypoints = md.map_moles()
        mole_b64 = base64.b64encode(moles_file)

        new_image = {"original": image, "moles": mole_b64}
        images['images'][orientation] = new_image

        orientation_moles = {"orientation": orientation, "moleData": []}

        for keypoint in moles_keypoints:
            mole = {"location": {"x": 0, "y": 0}, "asymmetry": "", "size": 0, "shape": "", "color": [0, 0, 0],
                    "misc": {}}
            location = keypoint.pt
            mole["location"]["x"] = location[0]
            mole["location"]["y"] = location[1]
            orientation_moles["moleData"].append(mole)

        all_moles["moles"].append(orientation_moles)

        # First check to make sure a previous entry exists
        mole_history = db.get_user_mole_history(user_id)
        if mole_history:
            # Get previous image and coordinates
            # image, prev_image: image format
            # coords, prev_coords: list([x,y])
            # NOTE: Images are currently Base 64 encoded for transmission purposes
            curr_image = base64.b64decode(image)
            prev_image = base64.b64decode(db.get_prev_image(user_id, orientation, 'original'))
            curr_coords = [[_mole["location"]["x"], _mole["location"]["y"]]
                      for _mole in orientation_moles["moleData"]]
            prev_coords = db.get_prev_coords(user_id, orientation)



            # TODO: Implement mole comparison and tracking here


    # Add images and mole data to database
    images_id = db.insert_images(images)
    all_moles["images_id"] = images_id
    db.update_user_mole_history(user_id, all_moles)

    result = images['images']
    for key in result.keys():
        result[key] = result[key]['moles']

    result["error"] = error["error"]
    response = json.dumps(result)
    return response

if __name__ == "__main__":
    port = 5000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    middleware.run(host="0.0.0.0", port=port, debug=True)
