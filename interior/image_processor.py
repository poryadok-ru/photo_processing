import os
from PIL import Image, ExifTags
from .config import Config

class ImageProcessor:
    """Класс для обработки изображений"""
    
    @staticmethod
    def get_image_orientation(img):
        """Определяет ориентацию изображения с учетом EXIF-данных"""
        try:
            exif = img._getexif()
            if exif:
                for tag, value in ExifTags.TAGS.items():
                    if value == 'Orientation':
                        orientation_tag = tag
                        break
                else:
                    return 1
                
                orientation = exif.get(orientation_tag, 1)
                return orientation
        except (AttributeError, KeyError, IndexError):
            pass
        return 1

    @staticmethod
    def apply_orientation(img, orientation):
        """Применяет правильную ориентацию к изображению"""
        if orientation == 1:
            return img
        elif orientation == 2:
            return img.transpose(Image.FLIP_LEFT_RIGHT)
        elif orientation == 3:
            return img.transpose(Image.ROTATE_180)
        elif orientation == 4:
            return img.transpose(Image.FLIP_TOP_BOTTOM)
        elif orientation == 5:
            return img.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.ROTATE_90)
        elif orientation == 6:
            return img.transpose(Image.ROTATE_270)
        elif orientation == 7:
            return img.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.ROTATE_270)
        elif orientation == 8:
            return img.transpose(Image.ROTATE_90)
        else:
            return img

    @staticmethod
    def extend_with_border_color(img, new_width, new_height):
        """Расширяет изображение до нужного размера, используя граничащие цвета"""
        width, height = img.size
        
        if width == new_width and height == new_height:
            return img
        
        new_img = Image.new('RGB', (new_width, new_height))
        x_offset = (new_width - width) // 2
        y_offset = (new_height - height) // 2
        
        new_img.paste(img, (x_offset, y_offset))
        
        has_left_right = width < new_width
        has_top_bottom = height < new_height
        
        # Заполняем левое и правое поля
        if has_left_right:
            for y in range(height):
                left_color = img.getpixel((0, y))
                right_color = img.getpixel((width - 1, y))
                
                for x in range(x_offset):
                    new_img.putpixel((x, y + y_offset), left_color)
                
                for x in range(x_offset + width, new_width):
                    new_img.putpixel((x, y + y_offset), right_color)
        
        # Заполняем верхнее и нижнее поля
        if has_top_bottom:
            for x in range(width):
                top_color = img.getpixel((x, 0))
                bottom_color = img.getpixel((x, height - 1))
                
                for y in range(y_offset):
                    new_img.putpixel((x + x_offset, y), top_color)
                
                for y in range(y_offset + height, new_height):
                    new_img.putpixel((x + x_offset, y), bottom_color)
        
        # Заполняем углы
        if has_left_right and has_top_bottom:
            top_left_color = img.getpixel((0, 0))
            top_right_color = img.getpixel((width - 1, 0))
            bottom_left_color = img.getpixel((0, height - 1))
            bottom_right_color = img.getpixel((width - 1, height - 1))
            
            for x in range(x_offset):
                for y in range(y_offset):
                    new_img.putpixel((x, y), top_left_color)
            
            for x in range(x_offset + width, new_width):
                for y in range(y_offset):
                    new_img.putpixel((x, y), top_right_color)
            
            for x in range(x_offset):
                for y in range(y_offset + height, new_height):
                    new_img.putpixel((x, y), bottom_left_color)
            
            for x in range(x_offset + width, new_width):
                for y in range(y_offset + height, new_height):
                    new_img.putpixel((x, y), bottom_right_color)
        
        return new_img

    @staticmethod
    def crop_to_3_4(image):
        """Обрезает изображение до точного соотношения 3:4"""
        width, height = image.size
        target_ratio = 3/4
        current_ratio = width / height
        
        if current_ratio > target_ratio:
            new_width = int(height * target_ratio)
            left = (width - new_width) // 2
            top = 0
            right = left + new_width
            bottom = height
        else:
            new_height = int(width / target_ratio)
            left = 0
            top = (height - new_height) // 2
            right = width
            bottom = top + new_height
        
        target_size=(1800, 2400)
        cropped_image = image.crop((left, top, right, bottom))
        resized_image = cropped_image.resize(target_size, resample=Image.LANCZOS)
        return resized_image

    def format_image_3_4(self, input_path, output_path, logger):
        """Приводит изображение к формату 3:4 с граничащими цветами"""
        try:
            with Image.open(input_path) as img:
                orientation = self.get_image_orientation(img)
                img = self.apply_orientation(img, orientation)
                
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                width, height = img.size
                target_ratio = 3/4
                current_ratio = width / height
                
                if current_ratio > target_ratio:
                    new_width = width
                    new_height = int(width / target_ratio)
                else:
                    new_height = height
                    new_width = int(height * target_ratio)
                
                new_img = self.extend_with_border_color(img, new_width, new_height)
                new_img.save(output_path, exif=b'')
                
                logger.info(f"Изображение приведено к формату 3:4: {width}x{height} -> {new_width}x{new_height}")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка при приведении к формату 3:4 {input_path}: {str(e)}")
            return False

    @staticmethod
    def save_image_simple(image, output_path, logger):
        """Простое сохранение изображения"""
        try:
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            image.save(output_path, "JPEG", quality=95)
            logger.info(f"Сохранено: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")
            return False