from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file, flash
from image_processor import collect_images, create_tiff
import requests
import shutil
import zipfile
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = 'secret_12908319028379834759873485'

app.config['UPLOAD_FOLDER'] = 'static/workfolder'
app.config['DOWNLOAD_FOLDER'] = 'static/downloads'

# Убеждаемся, что папки для загрузок и скачиваний существуют
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

@app.route('/', methods=['GET'])
def index():
    # Подготовка данных о статусе папок
    folder_path = app.config['UPLOAD_FOLDER']
    folders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
    folders_status = {folder: is_tiff_created(folder) for folder in folders}
    # Передача данных в шаблон
    return render_template('index.html', folders_status=folders_status)

def is_tiff_created(folder_name):
    """Проверяет, существует ли TIFF файл для данной папки."""
    tiff_file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], f"{folder_name}.tif")
    return os.path.exists(tiff_file_path)

def get_public_meta(public_key, path="/"):
    """Получение метаинформации о публичном ресурсе с учетом пути внутри публичной папки."""
    params = {"public_key": public_key, "path": path}
    url = "https://cloud-api.yandex.net/v1/disk/public/resources"
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json(), None
    else:
        return None, f"Ошибка при получении метаинформации: {response.status_code}, URL: {response.request.url}"

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

@app.route('/delete-folder/<folder_name>', methods=['POST'])
def delete_folder(folder_name):
    # Путь к папке, которую нужно удалить
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
    
    # Удаление папки и всех файлов в ней
    try:
        # Удаляем папку с файлами
        shutil.rmtree(folder_path)
        # Можно добавить удаление TIFF файла, если он существует
        tiff_file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], f"{folder_name}.tif")
        if os.path.exists(tiff_file_path):
            os.remove(tiff_file_path)
        flash(f"Folder '{folder_name}' and its TIFF file have been deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting folder '{folder_name}': {e}", "danger")
    
    # Перенаправление обратно на главную страницу
    return redirect(url_for('index'))

def download_file(download_url, save_path):
    """Скачивание файла."""
    response = requests.get(download_url, stream=True)
    if response.status_code == 200:
        with open(save_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        return True, f"Файл успешно скачан и сохранен в {save_path}"
    else:
        return False, f"Ошибка при скачивании файла: {response.status_code}"

def download_public_resource(public_key, save_dir, path="/"):
    """Скачивание публичного ресурса с учетом вложенных папок."""
    meta, error = get_public_meta(public_key, path=path)
    if error:
        return error

    downloaded_successfully = True

    if meta:
        if meta['type'] == 'file':
            file_name = os.path.basename(meta['path'])
            save_path = os.path.join(save_dir, file_name)
            success, message = download_file(meta['file'], save_path)
            if not success:
                downloaded_successfully = False
                return message
        elif meta['type'] == 'dir':
            for item in meta['_embedded']['items']:
                item_path = os.path.join(save_dir, item['name'])
                if item['type'] == 'file':
                    success, message = download_file(item['file'], item_path)
                    if not success:
                        downloaded_successfully = False
                        return message
                elif item['type'] == 'dir':
                    os.makedirs(item_path, exist_ok=True)
                    error = download_public_resource(public_key, item_path, path=item['path'])
                    if error and error != "Файлы успешно скачаны":
                        downloaded_successfully = False
                        return error

    if downloaded_successfully:
        return "Файлы успешно скачаны"
    else:
        return None

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

@app.route('/download', methods=['POST'])
def download_files():
    data = request.get_json()
    public_key = data['publicKey']
    save_dir = 'static/workfolder'

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    result = download_public_resource(public_key, save_dir)
    if result == "Файлы успешно скачаны":
        return jsonify({'success': True, 'message': result, 'reload': True})
    elif result is None:
        return jsonify({'success': False, 'error': 'Ошибка при скачивании файлов.'}), 500
    else:
        return jsonify({'success': False, 'error': result}), 500

if __name__ == '__main__':
    app.run()