from PIL import Image
import os

def collect_images(folder_paths):
    """
    Собирает изображения из списка папок.
    :param folder_paths: Список путей к папкам с изображениями.
    :return: Список объектов изображений PIL.
    """
    images = []
    for folder_path in folder_paths:
        for file_name in os.listdir(folder_path):
            if file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                img_path = os.path.join(folder_path, file_name)
                images.append(Image.open(img_path))
    return images

def create_tiff(images, output_path='static/downloads/Result.tif', images_per_row=4, padding=10):
    """
    Создает TIFF файл, размещая изображения в сетке с отступами.
    :param images: Список объектов изображений PIL.
    :param output_path: Путь к выходному файлу.
    :param images_per_row: Количество изображений в одной строке сетки.
    :param padding: Размер отступов между изображениями в пикселях.
    """
    if not images:
        print("No images to combine.")
        return

    # Определение размера сетки с учетом отступов
    max_width = max(image.width for image in images) + padding
    max_height = max(image.height for image in images) + padding
    total_rows = (len(images) + images_per_row - 1) // images_per_row

    # Создание нового изображения для сетки с учетом отступов
    grid_image_width = max_width * images_per_row + padding
    grid_image_height = max_height * total_rows + padding
    grid_image = Image.new('RGB', (grid_image_width, grid_image_height), 'white') # Заливка фона белым

    # Размещение изображений в сетке
    for i, image in enumerate(images):
        x = (i % images_per_row) * max_width + padding
        y = (i // images_per_row) * max_height + padding
        # Масштабирование изображения под размер сетки, если нужно
        if image.width != max_width - padding or image.height != max_height - padding:
            resized_image = image.resize((max_width - padding, max_height - padding), Image.ANTIALIAS)
        else:
            resized_image = image
        grid_image.paste(resized_image, (x, y))

    # Сохранение сетки изображений в файл
    grid_image.save(output_path, format="TIFF")
