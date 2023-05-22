import re
from flask import Flask, request, jsonify
from flasgger import Swagger, LazyString, LazyJSONEncoder, swag_from
import pandas as pd

app = Flask(__name__)
app.json_encoder = LazyJSONEncoder

# Inisialisasi data dictionary kamus untuk cleansing
kamus = pd.read_csv('new_kamusalay.csv', encoding='latin-1').set_index('slang').squeeze().to_dict()

# Inisialisasi data dictionary kata abusive untuk filter
abusive = pd.read_csv('abusive.csv', encoding='latin-1')
abusive_words = set(abusive['ABUSIVE'].str.lower())

# Merubah tulisan template halaman host 
swagger_template = dict(
    info = {
        'title': LazyString(lambda: 'API Challenge Gold'),
        'version': LazyString(lambda: '1.0.0'),
        'description': LazyString(lambda: 'API Documentation for Text Processing'),
    },
    host = LazyString(lambda: request.host)
)

# Konfigurasi Swagger
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "api",
            "route": "/api/spec",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api/docs/"
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

# Menentukan spesifikasi Swagger UI
@app.route('/api/spec')
def swagger_spec():
    return jsonify(swagger)

# Menghandle input teks melalui form
@app.route('/api/cleansing/form', methods=['POST'])
@swag_from("docs/input_data_form.yml", methods=['POST'])
def cleansing_form():
    text = request.form.get('text')
    # Membersihkan teks menggunakan regex
    cleaned_text = clean_text(text)

    return jsonify({'text':text,'cleaned_text': cleaned_text})

# Menghandle upload file CSV
@app.route('/api/cleansing/upload', methods=['POST'])
@swag_from("docs/input_data_upload.yml", methods=['POST'])
def cleansing_upload():
    file = request.files.get('file')
    
    if file and file.filename.endswith('.csv'):
        # Membaca file CSV ke DataFrame secara batch
        chunk_size = 10000  
        df_chunks = pd.read_csv(file, encoding='latin-1', chunksize=chunk_size)
        
        cleaned_data = []
        
        for chunk in df_chunks:
            # Membersihkan teks pada kolom 'tweet' menggunakan regex
            chunk['cleaned_text'] = chunk['Tweet'].apply(clean_text)
            cleaned_data.append(chunk)
        
        cleaned_df = pd.concat(cleaned_data)
        
        return jsonify(cleaned_df.to_dict(orient='records'))
    
    return jsonify({'error': 'Invalid file format'})

def clean_text(text):
    text = re.sub(r'https://t.co/\w+', '', text)  # hapus link dengan awalan https://t.co/
    text = re.sub(r'\\n+', ' ', text)  # hapus double backslash dan ganti newline dengan spasi
    text = re.sub(r'\s{2,}', ' ', text)  # ganti 2 atau lebih spasi berturut-turut dengan satu spasi
    text = re.sub(r'@\w+', '', text)  # hapus usename Twitter
    text = re.sub(r'#+\w*', '', text)  # hapus hashtag
    text = re.sub(r'[^a-zA-Z0-9]+', ' ', text)  # hapus karakter selain huruf dan angka
    text = re.sub(r'\bcc\b', '', text)  # hapus kata cc

    # Menghapus kata-kata abusive
    text = ' '.join(word for word in text.lower().split() if word not in abusive_words)

    # Membersihkan teks menggunakan kamus
    text = ' '.join(kamus.get(word, word) for word in text.split())

    return text.strip()

if __name__ == '__main__':
    app.run(debug=True)
