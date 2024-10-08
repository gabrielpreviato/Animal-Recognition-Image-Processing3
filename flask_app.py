from flask import Flask, render_template
from flask import request, jsonify

import skimage.color
import skimage.transform
import skimage.feature
import skimage.io
import os
import pickle
import numpy as np

import skimage

import uuid


app = Flask(__name__)

BASE_PATH = os.getcwd()
UPLOAD_PATH = os.path.join(BASE_PATH, 'static/upload/')
MODEL_PATH = os.path.join(BASE_PATH, 'static/models/')

## -------------------- Load Models -------------------
model_svc_path = os.path.join(MODEL_PATH, 'dsa_image_classification_svc.pickle')
scaler_path = os.path.join(MODEL_PATH, 'dsa_scaler.pickle')
model_svc = pickle.load(open(model_svc_path, 'rb'))
scaler = pickle.load(open(scaler_path, 'rb'))


@app.errorhandler(404)
def error404(error):
    message = "ERROR 404 OCCURED. Page Not Found. Please go the home page and try again"
    return render_template("error.html", message=message)  # page not found


@app.errorhandler(405)
def error405(error):
    message = 'Error 405, Method Not Found'
    return render_template("error.html", message=message)


@app.errorhandler(500)
def error500(error):
    message = 'INTERNAL ERROR 500, Error occurs in the program'
    return render_template("error.html", message=message)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == "POST":
        print('The request method is POST')
        if request.headers['Content-Type'] == 'application/octet-stream':
            # upload_file = request.data
            filename = uuid.uuid4().hex
            print('The filename that has been uploaded is ', filename)
            # know the extension of filename
            # all only .jpg, .png, .jpeg, PNG
            ext = 'jpg'
            print('The extension of the filename is ', ext)
            if ext.lower() in ['png', 'jpg', 'jpeg']:
                # saving the image
                path_save = os.path.join(UPLOAD_PATH, filename)
                # upload_file.save(path_save)
                with open(path_save, 'wb') as f:
                    f.write(request.data)
                    f.close()
                print('File saved sucessfully')
                # send to pipeline model
                results = pipeline_model(path_save, scaler, model_svc)
                hei = getheight(path_save)
                print(results)
                return jsonify(
                    results
                )
                #return render_template('upload.html', fileupload=True, extension=False, data=results,
                #                    image_filename=filename, height=hei)


            else:
                print('We only accept : .jpg, .png, .jpeg')

                return render_template('upload.html', extension=True, fileupload=False)

        else:
            return render_template('upload.html', fileupload=False, extension=False)


@app.route('/about/')
def about():
    return render_template('about.html')


def getheight(path):
    img = skimage.io.imread(path)
    h, w, _ = img.shape
    aspect = h / w
    given_width = 300
    height = given_width * aspect
    return height


def pipeline_model(path, scaler_transform, model):
    #pipeline model
    image = skimage.io.imread(path)

    #Transform image into 80 x 80
    image_resize = skimage.transform.resize(image, (80, 80))
    image_scale = 255*image_resize
    image_transform = image_scale.astype(np.uint8)

    #rgb to gray
    gray = skimage.color.rgb2gray(image_transform)
    #hog feature
    feature_vector = skimage.feature.hog(gray,
                                         orientations=9,
                                         pixels_per_cell=(8,8), cells_per_block=(3,3))

    #scaling
    scalex = scaler_transform.transform(feature_vector.reshape(1,-1))
    result = model.predict(scalex)

    #probability
    predicted_prob = model.predict_proba(scalex)
    predicted_prob = predicted_prob.flatten()
    labels = model.classes_

    top_5_prob_ind = predicted_prob.argsort()[::-1][:5]
    top_labels = labels[top_5_prob_ind]
    top_prob = predicted_prob[top_5_prob_ind]

    top_dict = dict()
    top = 0.0
    for key, val in zip(top_labels, top_prob):
        if val > top:
            top = val
            top_dict = {"pred": key, "probability": val}
        # top_dict.update({key: str(np.round(val,2)*100) + " %"})

    return top_dict


if __name__ == "__main__":
    app.run(debug=False)