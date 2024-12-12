from flask import Flask, request, jsonify
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = 'upload/'
ALLOWED_EXTENSIONS = {'txt', 'doc', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'csv', 'svg', 'mp4'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    files = request.files.getlist('file')

    if not files:
        return jsonify({"error": "No file selected"}), 400
    
    filenames = []

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            filenames.append(filename)

        else: 
            return jsonify({"error": "Invalid file type"}), 400
        
    return jsonify({"message": "Files uploaded successfully", "filenames": filenames}), 200

if __name__ == '__main__':
    app.run(debug=True)