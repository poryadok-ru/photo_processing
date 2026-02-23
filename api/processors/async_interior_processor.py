import io
from typing import List, Tuple
from fastapi import UploadFile
import asyncio
from PIL import Image

from .async_base import AsyncBaseProcessor
from interior.async_ai_client import AsyncAIClient, get_product_from_sheet_by_code, extract_six_digit_code
from interior.config import Config
from ..logging import CustomLogger
from interior.image_processor import ImageProcessor

class AsyncInteriorProcessor(AsyncBaseProcessor):
    """Асинхронный обработчик для интерьеров"""

    def __init__(self):
        super().__init__("interior")
        self.ai_client = AsyncAIClient()

    async def process_single(self, file: UploadFile, variant: int = 1) -> Tuple[bytes, str]:
        """
        Обрабатывает одно изображение.
        variant=1 — светлый скандинавский стиль,
        variant=2 — тёплый насыщенный стиль.
        Возвращает (bytes, filename) — одно изображение.
        """
        logger = CustomLogger("interior")
        img_proc = ImageProcessor()
        processing_type_name = "interior"
        try:
            logger.info(f"Начало обработки интерьера: {file.filename} (variant={variant})")

            # 1. Читаем файл
            image_data = await self.save_uploaded_file(file)

            # 2. Открываем, выравниваем ориентацию, конвертируем в RGB
            with Image.open(io.BytesIO(image_data)) as img:
                orientation = img_proc.get_image_orientation(img)
                img = img_proc.apply_orientation(img, orientation)
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # 3. Форматируем в 3:4 с бордюрами
                width, height = img.size
                target_ratio = 3 / 4
                current_ratio = width / height
                if current_ratio > target_ratio:
                    new_width = width
                    new_height = int(width / target_ratio)
                else:
                    new_height = height
                    new_width = int(height * target_ratio)
                img_3_4 = img_proc.extend_with_border_color(img, new_width, new_height)

                buf_3_4 = io.BytesIO()
                img_3_4.save(buf_3_4, format="JPEG", quality=95)
                img_3_4_bytes = buf_3_4.getvalue()

            # 4. Определяем категорию (Google Sheets → AI fallback)
            product_name = None
            subcategory = None
            main_category = None
            use_custom_prompt = False

            code = extract_six_digit_code(filename=file.filename)
            if code:
                sheet_row = await get_product_from_sheet_by_code(code, logger)
                if sheet_row:
                    subcategory, product_name = sheet_row
                    use_custom_prompt = True
                    logger.info(f"Из Google Sheets: Категория={subcategory}, Номенклатура={product_name} для кода {code}")
                else:
                    logger.info(f"Код {code} не найден в Google Sheets. Используется определение через AI.")
                    async with self.semaphore:
                        main_category, subcategory = await self.ai_client.analyze_thematic_subcategory(
                            img_3_4_bytes, logger
                        )
            else:
                logger.info("В имени файла не найден 6-значный код. Используется определение через AI.")
                async with self.semaphore:
                    main_category, subcategory = await self.ai_client.analyze_thematic_subcategory(
                        img_3_4_bytes, logger
                    )

            # 5. Строим промпт под нужный вариант
            prompt = self._generate_context_prompt(
                main_category=main_category if not use_custom_prompt else None,
                subcategory=subcategory,
                product_name=product_name,
                use_custom=use_custom_prompt,
                variant=variant,
            )
            logger.info(f"Категория для {file.filename}: {main_category} - {subcategory}, variant={variant}")

            # 6. Генерируем одно изображение
            async with self.semaphore:
                raw_data = await self.ai_client.edit_image_with_gemini(
                    img_3_4_bytes, prompt, logger, variant=variant
                )

            if not raw_data:
                raise Exception(f"Image generation failed for variant={variant}")

            # 7. Кроп до 3:4 и сохранение
            processed_image = Image.open(io.BytesIO(raw_data))
            cropped_image = img_proc.crop_to_3_4(processed_image)
            output_buffer = io.BytesIO()
            cropped_image.save(output_buffer, format="JPEG", quality=95)
            processed_bytes = output_buffer.getvalue()

            name_base = file.filename.rsplit('.', 1)[0]
            suffix = "processed" if use_custom_prompt else f"in_{main_category.lower()}"
            output_filename = f"{name_base}_{suffix}_v{variant}.jpg"

            logger.info(f"{processing_type_name} | Успешно обработан: {file.filename} variant={variant}")
            logger.finish_success(
                filename=file.filename,
                processing_type=processing_type_name,
                category=main_category,
                subcategory=subcategory,
            )
            return processed_bytes, output_filename

        except Exception as e:
            logger.error(f"{processing_type_name} | Ошибка при обработке {file.filename}: {e}")
            logger.finish_error(processing_type=processing_type_name, error=str(e))
            raise

    # ── Стили интерьера ────────────────────────────────────────────────────────
    _VARIANT_STYLES = {
        1: {
            "label": "light & natural",
            "description": (
                "Light, airy Scandinavian-inspired setting. "
                "Soft natural daylight from a window, neutral white or warm beige tones, "
                "clean minimal surfaces, light wood textures, subtle plant or linen accents. "
                "Bright and fresh atmosphere."
            ),
        },
        2: {
            "label": "rich & moody",
            "description": (
                "Rich, warm and cozy atmosphere. "
                "Warm artificial light (soft lamps or candles), deep earthy or dark tones — "
                "terracotta, charcoal, navy or forest green, "
                "textured surfaces such as stone, dark wood or velvet. "
                "Intimate and premium feel."
            ),
        },
    }

    # Общий блок про линейку — одинаковый для обоих промптов
    _RULER_BLOCK = (
        "SCALE REFERENCE (ruler):\n"
        "- The input image MAY contain a centimeter ruler placed next to the product.\n"
        "- If a ruler is visible, use it ONLY to determine the exact real-world size of the product.\n"
        "- The product must appear in the output at its true physical scale relative to the interior "
        "(e.g. if the ruler shows the product is 12 cm tall, it must look like a 12 cm object in a real room).\n"
        "- Do NOT make the product larger or smaller than its actual size.\n"
        "- Remove the ruler from the final image — it must NOT appear in the output."
    )

    # Общий блок про кадрирование — одинаковый для обоих промптов
    _FRAMING_BLOCK = (
        "FRAMING & PROXIMITY — CRITICAL:\n"
        "- This is a CLOSE-UP product shot. The camera must be positioned CLOSE to the product.\n"
        "- The product must fill AT LEAST 60-70% of the frame height.\n"
        "- Think of it as a macro product photo: the product is front and center, large and dominant.\n"
        "- DO NOT place the product far away in a wide room shot — no full-room views, no distant perspectives.\n"
        "- DO NOT show large empty spaces around the product.\n"
        "- The background/interior is only a narrow, blurred context strip — it should NOT compete with the product.\n"
        "- Imagine the photographer walked up close and pointed the camera directly at the product from 0.5-1.5 meters away."
    )

    def _generate_context_prompt(
        self,
        main_category: str | None = None,
        subcategory: str | None = None,
        product_name: str | None = None,
        use_custom: bool = False,
        variant: int = 1,
    ) -> str:
        """
        Строит промпт для нужного варианта стиля.
        Блок про линейку присутствует в обоих вариантах.
        Категорийная логика (use_custom / main_category / subcategory) не затрагивается.
        """
        style = self._VARIANT_STYLES.get(variant, self._VARIANT_STYLES[1])
        style_block = (
            f"INTERIOR STYLE (variant {variant} — {style['label']}):\n"
            f"- {style['description']}\n"
            f"- This style must define the background mood, lighting and color palette.\n"
            f"- The product itself must remain UNCHANGED — only the environment changes."
        )

        if use_custom:
            extra_info = []
            if product_name:
                extra_info.append(f"- Product name: {product_name}")
            if subcategory:
                extra_info.append(f"- Product category: {subcategory}")
            extra = "\n".join(extra_info)
            prompt = f"""
CREATE NATURAL PRODUCT PHOTO IN CONTEXT, using the following product information (do not add this information to the photo, just use it for context):
{extra}

{style_block}

{self._RULER_BLOCK}

LOCATION:
- Create a NEUTRAL environment or setting that is best suited for a product with this name and category.
- The background and context should NOT belong to any specific place (like kitchen, bathroom, garden, etc.),
  but should fit naturally for this type of product and category.
- Ensure the setting highlights the product appropriately, playing up its intended use, but without strong associations to a specific room.
PRODUCT PRESERVATION:
- Use the EXACT same product from the input image (same angle, orientation, and position).
- Do NOT change the product's perspective or viewing angle.
- Preserve all product details, colors, and textures exactly as shown.
- Keep all text, labels, and logos unchanged.
{self._FRAMING_BLOCK}

COMPOSITION & STYLING:
- Product must remain the main focus of the image.
- The background should be soft and strongly blurred — background details should not be clearly legible.
- Add minimal, non-distracting contextual props relevant to the product type.
FINAL OUTPUT:
- High-quality professional close-up photography of the product.
- The product is large, sharp, and dominant — the interior is atmosphere, not subject.
- Realistic scale consistent with the interior environment.
- No ruler or measurement markings in the output.
"""
        else:
            context = Config.THEMATIC_SUBCATEGORIES.get(main_category, {}).get(
                subcategory, "neutral interior setting"
            )
            prompt = f"""
CREATE NATURAL PRODUCT PHOTO IN CONTEXT:

{style_block}

{self._RULER_BLOCK}

PRODUCT PRESERVATION:
- Use the EXACT same product from the input image.
- Maintain the SAME angle, orientation, and position as in the original photo.
- Do NOT change the product's perspective or viewing angle.
- Preserve all product details, colors, textures exactly as shown.
- Keep all text, labels, logos completely unchanged.
CONTEXT AND SETTING:
- Place the product in a {main_category.lower()} environment: {context}
- The product should appear naturally placed in this setting.
- Maintain realistic scale relative to the surrounding interior.
BACKGROUND AND COMPOSITION:
- Create a soft, slightly blurred background that matches {main_category} aesthetic and the INTERIOR STYLE above.
- Background should be authentic but not distracting from the product.
- Use lighting consistent with the INTERIOR STYLE — natural daylight for variant 1, warm lamp light for variant 2.
- Add subtle contextual elements that make sense for {subcategory.lower()}.
{self._FRAMING_BLOCK}

STYLING GUIDELINES:
- The scene should look realistic and professionally styled.
- Keep the composition clean and uncluttered.
TECHNICAL REQUIREMENTS:
- High-quality professional photography.
- Product appearance must be identical to input (only environment changes).
- Strong background blur — the interior context should be soft and out of focus.
- No ruler or measurement markings in the output.
FINAL OUTPUT: Close-up product photo in appropriate {main_category} context, styled as described in INTERIOR STYLE above. The product is the hero of the shot — large, sharp, dominant. The interior is visible but blurred behind it.
"""
        return prompt

    def _crop_to_3_4(self, image: Image.Image) -> Image.Image:
        """Обрезает изображение до 3:4 (синхронно)"""
        width, height = image.size
        target_ratio = 3 / 4
        if width / height > target_ratio:
            new_width = int(height * target_ratio)
            left = (width - new_width) // 2
            return image.crop((left, 0, left + new_width, height))
        else:
            new_height = int(width / target_ratio)
            top = (height - new_height) // 2
            return image.crop((0, top, width, top + new_height))

    async def process_batch(self, files: List[UploadFile]) -> io.BytesIO:
        """Обрабатывает батч файлов для интерьеров (variant не используется — batch идёт через parallel)"""
        logger = CustomLogger("interior")
        try:
            logger.info(f"Начало пакетной обработки {len(files)} файлов")

            tasks = [self.process_single(file) for file in files]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            successful_results = []
            error_count = 0

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_count += 1
                    logger.error(f"Ошибка обработки {files[i].filename}: {result}")
                else:
                    processed_data, filename = result
                    successful_results.append((filename, processed_data))

            if not successful_results:
                logger.finish_error(error="All processing failed")
                raise Exception("All images failed to process")

            zip_buffer = await self.create_zip_response(successful_results)

            logger.info(f"Пакетная обработка завершена. Файлов: {len(successful_results)}, Ошибок: {error_count}")
            logger.finish_success(
                processed_count=len(successful_results),
                error_count=error_count,
                total_files=len(files),
            )
            return zip_buffer

        except Exception as e:
            logger.error(f"Ошибка пакетной обработки: {e}")
            logger.finish_error(error=str(e))
            raise