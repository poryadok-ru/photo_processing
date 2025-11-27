-- Заполнение тематических категорий
INSERT INTO thematic_categories (main_category, subcategory, description) VALUES
-- KITCHEN
('KITCHEN', 'COOKWARE', 'Кастрюли, сковороды, посуда для готовки'),
('KITCHEN', 'UTENSILS', 'Столовые приборы, ножи, кухонные инструменты'),
('KITCHEN', 'APPLIANCES', 'Кухонная техника, тостеры, блендеры'),
('KITCHEN', 'STORAGE', 'Контейнеры, банки, системы хранения'),
('KITCHEN', 'DINNERWARE', 'Тарелки, чашки, сервировочная посуда'),
('KITCHEN', 'DECOR', 'Кухонный декор, полотенца, аксессуары'),

-- BATHROOM
('BATHROOM', 'TOWELS', 'Полотенца, банные халаты'),
('BATHROOM', 'HYGIENE', 'Средства личной гигиены, мыло, шампуни'),
('BATHROOM', 'FURNITURE', 'Ванная мебель, шкафчики, полки'),
('BATHROOM', 'STORAGE', 'Органайзеры, корзины, системы хранения'),
('BATHROOM', 'ACCESSORIES', 'Держатели, крючки, аксессуары'),
('BATHROOM', 'CLEANING', 'Средства для уборки, щетки'),

-- LIVING_ROOM
('LIVING_ROOM', 'FURNITURE', 'Диваны, кресла, столы, стеллажи'),
('LIVING_ROOM', 'LIGHTING', 'Лампы, светильники, торшеры'),
('LIVING_ROOM', 'DECOR', 'Декор, вазы, картины, зеркала'),
('LIVING_ROOM', 'TEXTILES', 'Подушки, покрывала, ковры'),
('LIVING_ROOM', 'STORAGE', 'Полки, тумбы, системы хранения'),
('LIVING_ROOM', 'ELECTRONICS', 'Телевизоры, аудиосистемы'),

-- BEDROOM
('BEDROOM', 'BEDDING', 'Постельное белье, подушки, одеяла'),
('BEDROOM', 'FURNITURE', 'Кровати, тумбочки, шкафы'),
('BEDROOM', 'LIGHTING', 'Прикроватные лампы, светильники'),
('BEDROOM', 'DECOR', 'Декор, картины, аксессуары'),
('BEDROOM', 'STORAGE', 'Комоды, органайзеры, коробки'),
('BEDROOM', 'TEXTILES', 'Пледы, покрывала, коврики'),

-- OFFICE
('OFFICE', 'FURNITURE', 'Столы, стулья, полки'),
('OFFICE', 'ORGANIZATION', 'Органайзеры, лотки, системы хранения'),
('OFFICE', 'STATIONERY', 'Канцелярия, ручки, блокноты'),
('OFFICE', 'TECH', 'Компьютерные аксессуары, настольные лампы'),
('OFFICE', 'DECOR', 'Офисный декор, растения, картины'),

-- HOLIDAY
('HOLIDAY', 'CHRISTMAS', 'Ёлочные игрушки, рождественские украшения, гирлянды'),
('HOLIDAY', 'EASTER', 'Пасхальные украшения, фигурки, корзины, яйца'),
('HOLIDAY', 'HALLOWEEN', 'Хэллоуинский декор, тыквы, свечи, тематические фигурки'),
('HOLIDAY', 'NEW_YEAR', 'Украшения к Новому году, мишура, шары, звёзды'),
('HOLIDAY', 'VALENTINE', 'Украшения ко Дню Святого Валентина, сердечки, свечи'),
('HOLIDAY', 'GENERAL', 'Праздничный декор и универсальные украшения')

ON CONFLICT (main_category, subcategory) DO NOTHING;
