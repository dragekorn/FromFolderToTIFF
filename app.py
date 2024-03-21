# from flask import Flask, request, render_template, send_file, redirect, url_for
# import zipfile
# import os
# from image_processor import collect_images, create_tiff
# from werkzeug.utils import secure_filename

# app = Flask(__name__)
# app.config['UPLOAD_FOLDER'] = 'static/workfolder'

# @app.route('/', methods=['GET'])
# def index():
#     folder_path = os.path.join(app.config['UPLOAD_FOLDER'])
#     if not os.path.exists(folder_path):
#         os.makedirs(folder_path)
#     folders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
#     return render_template('index.html', folders=folders)

# # Определение маршрута для обработки ZIP файлов
# @app.route('/upload-zip', methods=['POST'])
# def upload_zip():
#     if 'zip_file' not in request.files:
#         return redirect(request.url)
#     file = request.files['zip_file']
#     if file.filename == '':
#         return redirect(request.url)
#     if file:
#         filename = secure_filename(file.filename)
#         zip_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#         file.save(zip_path)
#         with zipfile.ZipFile(zip_path, 'r') as zip_ref:
#             extract_path = os.path.splitext(zip_path)[0]
#             zip_ref.extractall(extract_path)
#         os.remove(zip_path)  # Удаляем ZIP-архив после распаковки
#         return redirect(url_for('index'))

# # Определение маршрута для обработки данных формы
# @app.route('/generate-tiff', methods=['POST'])
# def generate_tiff():
#     try:
#         # Получаем список папок из формы
#         folder_list = request.form.get('folder_list')
#         if not folder_list:
#             return "Please provide a list of folders.", 400

#         # Преобразуем строку в список папок
#         folder_paths = folder_list.split(',')

#         # Собираем изображения из папок
#         images = collect_images(folder_paths)

#         if not images:
#             return "No images found in the provided folders.", 404

#         # Генерируем TIFF файл
#         output_path = 'static/downloads/Result.tif'
#         create_tiff(images, output_path)

#         # Предлагаем пользователю скачать файл
#         return send_file(output_path, as_attachment=True)
#     except Exception as e:
#         # Логирование исключения (можно расширить логирование в зависимости от требований проекта)
#         print(f"An error occurred: {e}")
#         return "An error occurred while processing your request.", 500

# if __name__ == '__main__':
#     app.run(debug=True)

from flask import Flask, request, render_template, send_file, redirect, url_for
import requests
from PIL import Image
import zipfile
import os
import io
from werkzeug.utils import secure_filename
from image_processor import collect_images, create_tiff

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/workfolder'
app.config['DOWNLOAD_FOLDER'] = 'static/downloads'

# Убедитесь, что папки для загрузок и скачиваний существуют
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)


ACCESS_TOKEN = "y0_AgAAAAADSm5IAAt8cgAAAAD--d4gAAAJiluK0SZCj5cMDApH-xTA9-NB2A"

@app.route('/', methods=['GET'])
def index():
    folder_path = app.config['UPLOAD_FOLDER']
    folders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
    folders_status = {folder: is_tiff_created(folder) for folder in folders}
    return render_template('index.html', folders_status=folders_status)

@app.route('/upload-zip', methods=['POST'])
def upload_zip():
    if 'zip_file' not in request.files:
        return redirect(request.url)
    file = request.files['zip_file']
    if file.filename == '':
        return redirect(request.url)
    if file:
        filename = secure_filename(file.filename)
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(zip_path)

        # Распаковываем ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            extract_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.splitext(filename)[0])
            zip_ref.extractall(extract_path)

        os.remove(zip_path)  # Удаляем ZIP-архив после распаковки

        # Проверяем, есть ли в распакованной папке одна вложенная папка
        contents = os.listdir(extract_path)
        if len(contents) == 1 and os.path.isdir(os.path.join(extract_path, contents[0])):
            nested_folder_path = os.path.join(extract_path, contents[0])
            # Проверяем, содержит ли вложенная папка изображения
            if any(file.lower().endswith(('.png', '.jpg', '.jpeg')) for file in os.listdir(nested_folder_path)):
                # Если да, то перемещаем содержимое вложенной папки на уровень выше
                for file in os.listdir(nested_folder_path):
                    os.rename(os.path.join(nested_folder_path, file), os.path.join(extract_path, file))
                # Удаляем теперь пустую вложенную папку
                os.rmdir(nested_folder_path)

        return redirect(url_for('index'))

@app.route('/generate-tiff/<folder_name>', methods=['POST'])
def generate_folder_tiff(folder_name):
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
    images = collect_images([folder_path])
    if not images:
        return "No images found in the folder.", 404

    output_path = os.path.join(app.config['DOWNLOAD_FOLDER'], f"{folder_name}.tif")
    create_tiff(images, output_path)

    return redirect(url_for('index'))

@app.route('/download-tiff/<folder_name>', methods=['GET'])
def download_tiff(folder_name):
    tiff_file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], f"{folder_name}.tif")
    if os.path.exists(tiff_file_path):
        return send_file(tiff_file_path, as_attachment=True)
    else:
        return "TIFF file not found.", 404

def is_tiff_created(folder_name):
    """Проверяет, существует ли TIFF файл для данной папки."""
    tiff_file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], f"{folder_name}.tif")
    return os.path.exists(tiff_file_path)

@app.route('/process-external-source', methods=['POST'])
def process_external_source():
    public_url = request.form.get('external_url')
    output_path = os.path.join(app.config['DOWNLOAD_FOLDER'], 'Result.tif')
    
    # Сначала преобразуем публичную ссылку в public_key
    public_key = public_url.split('/')[-1]
    # Скачиваем файлы
    download_and_convert_images(public_key, output_path, ACCESS_TOKEN)
    
    # После создания .tif файла предлагаем его для скачивания
    return send_file(output_path, as_attachment=True)

def download_and_convert_images(public_key, output_path, access_token):
    """Downloads images from the public Yandex.Disk folder and converts them to TIFF."""
    headers = {'Authorization': f'OAuth {access_token}'}
    download_folder = os.path.join(os.path.dirname(output_path), 'temp_downloads')
    os.makedirs(download_folder, exist_ok=True)

    # Получаем список ссылок для скачивания
    download_links = get_public_files_download_links(public_key, access_token)
    for url in download_links:
        download_file(url, download_folder, headers)
    
    # Обрабатываем скачанные изображения
    images = collect_images([download_folder])
    if images:
        create_tiff(images, output_path)

        # Удаляем временную папку с изображениями
        for file in os.listdir(download_folder):
            os.remove(os.path.join(download_folder, file))
        os.rmdir(download_folder)
    else:
        print("Не удалось найти изображения по указанной ссылке.")

def get_public_files_download_links(public_key, access_token):
    """Получает список прямых ссылок для скачивания файлов из публичной папки."""
    public_resources_url = f"https://cloud-api.yandex.net/v1/disk/public/resources/download?public_key={public_key}"
    headers = {'Authorization': f'OAuth {access_token}'}
    response = requests.get(public_resources_url, headers=headers)
    download_links = []
    if response.status_code == 200:
        download_link = response.json().get('href')
        if download_link:
            download_links.append(download_link)
    return download_links

def download_file(file_url, download_folder, headers):
    """Скачивает файл."""
    local_filename = file_url.split('/')[-1]
    path = os.path.join(download_folder, local_filename)
    with requests.get(file_url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with open(path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): 
                f.write(chunk)
    return local_filename


if __name__ == '__main__':
    app.run(debug=True)
