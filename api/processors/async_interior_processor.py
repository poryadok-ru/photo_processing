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

    async def process_single(self, file: UploadFile, scene_index: int = 0) -> Tuple[bytes, str]:
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
            logger.info(f"Начало обработки интерьера: {file.filename} (scene_index={scene_index})")

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
                scene_index=scene_index,
            )
            logger.info(f"Категория для {file.filename}: {main_category} - {subcategory}, scene_index={scene_index}")

            # 6. Генерируем одно изображение
            async with self.semaphore:
                raw_data = await self.ai_client.edit_image_with_gemini(
                    img_3_4_bytes, prompt, logger
                )

            if not raw_data:
                raise Exception(f"Image generation failed for scene_index={scene_index}")

            # 7. Кроп до 3:4 и сохранение
            processed_image = Image.open(io.BytesIO(raw_data))
            cropped_image = img_proc.crop_to_3_4(processed_image)
            output_buffer = io.BytesIO()
            cropped_image.save(output_buffer, format="JPEG", quality=95)
            processed_bytes = output_buffer.getvalue()

            name_base = file.filename.rsplit('.', 1)[0]
            suffix = "processed" if use_custom_prompt else f"in_{main_category.lower()}"
            output_filename = f"{name_base}_{suffix}.jpg"

            logger.info(f"{processing_type_name} | Успешно обработан: {file.filename} scene_index={scene_index}")
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

    # ── Пул цветовых акцентов — влияют только на палитру, не диктуют композицию ─
    # Роутер случайно выбирает индекс. Сцену модель подбирает сама по категории.
    _COLOR_ACCENTS = [
        {
            "label": "pure white & light",
            "palette": (
                "Background palette: pure white and very light grey tones. "
                "Crisp, clean, bright. Minimal color — let the product stand out."
            ),
        },
        {
            "label": "warm sand & linen",
            "palette": (
                "Background palette: warm sandy beige, cream, and soft linen tones. "
                "Warm natural light. Cozy and inviting without being heavy."
            ),
        },
        {
            "label": "soft sage & muted green",
            "palette": (
                "Background palette: muted sage green, dusty eucalyptus, and off-white. "
                "Fresh and natural feel. Light and airy, not saturated."
            ),
        },
        {
            "label": "blush & warm rose",
            "palette": (
                "Background palette: very soft blush pink, warm rose-white, and light peach tones. "
                "Delicate and elegant. Light-toned, never dark."
            ),
        },
        {
            "label": "pale blue & cool grey",
            "palette": (
                "Background palette: pale sky blue, cool light grey, and white. "
                "Fresh and airy. Clean and modern without being cold."
            ),
        },
        {
            "label": "warm terracotta & oat",
            "palette": (
                "Background palette: very light terracotta, warm oat, and natural clay tones. "
                "Earthy but bright. Sun-warmed feel, always light-toned."
            ),
        },
    ]

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
        scene_index: int = 0,
    ) -> str:
        """
        Строит промпт. Сцену модель выбирает сама по категории/названию товара.
        Варьируется только цветовой акцент фона (scene_index → _COLOR_ACCENTS).
        """
        accent = self._COLOR_ACCENTS[scene_index % len(self._COLOR_ACCENTS)]
        color_block = (
            f"BACKGROUND COLOR PALETTE ({accent['label']}):\n"
            f"- {accent['palette']}\n"
            f"- Always light-toned: background must NEVER be dark or heavily saturated.\n"
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
TASK: Add a natural, contextually appropriate background to this product photo. The product must remain 100% unchanged.

PRODUCT INFORMATION (context only — do not display in the image):
{extra}

PRODUCT PRESERVATION — HIGHEST PRIORITY:
- Copy the product from the input image EXACTLY as-is: same shape, same colors, same quantity of items, same angle, same orientation.
- DO NOT add, remove, or change any part of the product itself.
- DO NOT change the number of items (if there are 3 bottles, keep exactly 3 bottles).
- Preserve every detail: colors, textures, labels, logos, text, packaging.
- The product in the output must be INDISTINGUISHABLE from the product in the input.

BACKGROUND SCENE — choose freely based on the product:
- Pick the most natural, logical real-world setting for this specific product.
- Let the product category and name guide your choice: cleaning products → bathroom or kitchen; garden supplies → outdoors or balcony; cookware → kitchen; textiles → bedroom or living room; etc.
- The scene should feel genuinely appropriate — like a real lifestyle photo for this product.
- Be creative with the composition, props, and setting — make it feel alive, not generic.

{color_block}

{self._RULER_BLOCK}

{self._FRAMING_BLOCK}

COMPOSITION:
- Product is the clear hero: large, sharp, front and center.
- Background is soft, blurred, and subordinate to the product.
- Add 1-2 contextually fitting props at most — keep it natural, not cluttered.
FINAL OUTPUT:
- Professional close-up product photo with a natural, product-appropriate background.
- Product: identical to input. Color palette: {accent["label"]}.
- No ruler or measurement markings.
"""
        else:
            context = Config.THEMATIC_SUBCATEGORIES.get(main_category, {}).get(
                subcategory, "neutral interior setting"
            )
            prompt = f"""
TASK: Add a natural, contextually appropriate background to this product photo. The product must remain 100% unchanged.

PRODUCT PRESERVATION — HIGHEST PRIORITY:
- Copy the product from the input image EXACTLY as-is: same shape, same colors, same quantity of items, same angle, same orientation.
- DO NOT add, remove, or change any part of the product itself.
- DO NOT change the number of items (if there are 3 bottles, keep exactly 3 bottles).
- Preserve every detail: colors, textures, labels, logos, text, packaging.
- The product in the output must be INDISTINGUISHABLE from the product in the input.

BACKGROUND SCENE:
- Place the product in a {main_category.lower()} setting: {context}
- Make the scene feel alive and authentic for {subcategory.lower()} — not generic or template-like.
- Be creative with composition, angle, and contextual props. Let the product category inspire the scene.

{color_block}

{self._RULER_BLOCK}

{self._FRAMING_BLOCK}

COMPOSITION:
- Product is the clear hero: large, sharp, front and center.
- Background is soft, blurred, and subordinate to the product.
- Add subtle, natural props appropriate for {subcategory.lower()}.
- Keep the composition clean and uncluttered.
FINAL OUTPUT:
- Professional close-up product photo in a natural {main_category.lower()} setting.
- Product: identical to input. Scene: {context}. Color palette: {accent["label"]}.
- No ruler or measurement markings.
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