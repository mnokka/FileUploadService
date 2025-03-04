import os
import hashlib
import json
from flask import Flask, request, jsonify
import logging
#import shutil
#import gzip


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)

UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
DATA_FILE = os.getenv('DATA_FILE', 'data/names_and_hashes.json')

###################################################################################
# Calculate has has over the file, using 8192 chunk size for calculations
#
def calculate_file_hash(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

###################################################################################
#
# Save and compress given file
# Skipped now as .npg pic gzipping does not offer much space saving
# Also hash changes for same pic if redone
#
def save_and_compress_file(file, target_folder, name):
    """
    Save and compress to gzip given file.
    Return saved packed file path and hash to file.
    """
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    original_path = os.path.join(target_folder, file.filename)
    file.save(original_path)
    
    compressed_path = original_path + '.gz'
    
    with open(original_path, 'rb') as src, gzip.open(compressed_path, 'wb') as dst:
        shutil.copyfileobj(src, dst)

    file_hash = calculate_file_hash(compressed_path)

    os.remove(original_path)

    logging.info(f"File saved and compressed to {compressed_path}, hash:{file_hash}")
    
    return compressed_path, file_hash



###################################################################################
# Upload image and name
# 
# curl -X POST -F "name=Mika" -F "file=@kuva.png" http://localhost:5000/upload
#
@app.route('/upload', methods=['POST'])
def upload_file():
    logging.info(f"** UPLOAD SECTION ****")
    name = request.form.get('name')
    file = request.files.get('file')

    if not name or not file:
        return jsonify({'error': 'Name and file required'}), 400

    logging.info(f"Received data, name:{name} ,file:{file}")

    if not hasattr(file, 'read'):
        logging.error(f"ERROR: File is not a valid FileStorage object: {file}")
        return jsonify({'error': 'Invalid file format'}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    try:
        file.save(filepath)
        logging.info(f"File saved to {filepath}")
    except Exception as e:
        logging.error(f"Failed to save file({filepath}): {e}")
        return jsonify({'error': f'Failed to save file: {str(e)}'}), 500

    #try:
        #_, file_hash = save_and_compress_file(file, UPLOAD_FOLDER, name)
    #except Exception as e:
    #    logging.error(f"Failed to save/compress file: {e}")
    #    return jsonify({'error': f'Failed to save file: {str(e)}'}), 500
    
    file_hash = calculate_file_hash(filepath)
    logging.info(f"File:{file}, file_hash:{file_hash}")


    # save name + hash of pic. Owerrite existing file everytime with new data
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
               
                try:
                    data = json.load(f)
                    logging.info(f"Old data:{data}")
                except json.JSONDecodeError:
                    logging.warning("Data file is empty or corrupted, starting with empty data.")
                    data = {}  
        else:
            data = {}
            logging.info(f"No existing data found")
        
        if file_hash in data:
            logging.info(f"File with hash {file_hash} already exists. Updating name...")
        else:
            logging.info(f"New file with hash {file_hash} detected. Adding new entry.")


        data[file_hash] = name

        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)


    except Exception as e:
            logging.error(f"Unexpected error: {e}")
            return jsonify({'error': f'Failed to save data: {str(e)}'}), 500

    return jsonify({'message': 'Upload successful', 'file_hash': file_hash})


##########################################################################
# Get hash (image name) name
#
# curl -X GET http://localhost:5000/lookup/234dd59656f803ce7b553579dcf0054ac236032a838f462ef5425d8dc023db4f
#
@app.route('/lookup/<file_hash>', methods=['GET'])
def lookup(file_hash):
    logging.info(f"*** Checking hash {file_hash}*** ")
    if os.path.exists(DATA_FILE):
       
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                name = data.get(file_hash)
                if name:
                    logging.info(f"OK: Hash:{file_hash} ---> {name}")
                    return jsonify({'name': name})
                else: 
                    logging.error(f"ERROR.Hash:{file_hash} not found")
                    return jsonify({'error': 'Hash not found'}), 404
        
        except json.JSONDecodeError as e:
            logging.error(f"Error reading data file({DATA_FILE}): {e}")
            return jsonify({'error': 'Data file corrupted'}), 500
    else:
        logging.error(f"Error. Hash file not found")
        return jsonify({'error': 'Hash file not found'}), 404

################################################################################

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
