from __future__ import annotations

import os

LANGS = {
    'uk_UA': {
        # Повідомлення операторів
        ('MESH_OT_select_path', "Can not redo anymore"): "Більше нічого касувати",
        ('MESH_OT_select_path', "Closed active path"): "Замкнуто активний шлях",
        ('MESH_OT_select_path', "Closed path"): "Шлях замкнуто",
        ('MESH_OT_select_path', "Merged adjacent control elements"): "Об'єднано сусідні контрольні елементи",
        ('MESH_OT_select_path', "Joined two paths"): "Об'єднано два шляхи",
        ('MESH_OT_select_path', "Created new path"): "Створено новий шлях",

        # Користувацькі налаштування.
        ('Preferences', "Tab"): "Вкладка",
        ('*', "User preferences tab to be displayed"): "Вкладка користувацьких налаштувань яку буде відображено",
        ('Preferences', "Appearance"): "Відображення",
        ('*', "Appearance settings"): "Налаштування відображення",
        ('Preferences', "Behavior"): "Поведінка",
        ('*', "Behavior settings"): "Налаштування поведінки",
        ('Preferences', "Keymap"): "Клавіші",
        ('*', "Keymap settings"): "Налаштування розкладки клавіатурних скорочень",
        ('Preferences', "Info"): "Інформація",
        ('*', (
            "How to use the addon, relative links and licensing information"
        )): (
            "Як користуватися додатком, корисні посилання та інформація про ліцензію"
        ),

        ('Preferences', "Release Notes"): "Про Випуск",
        ('Preferences', "BlenderHQ on GitHub"): "BlenderHQ на GitHub",

        ('Preferences', "Control Element"): "Контрольний Елемент",
        ('*', "Control element color"): "Колір контрольного елементу",
        ('Preferences', "Active Control Element"): "Активний Контрольний Елемент",
        ('*', "Color of active control element"): "Колір активного контрольного елементу",
        ('Preferences', "Path"): "Шлях",
        ('*', "Regular path color"): "Колір звичайного шляху",
        ('Preferences', "Topology Path"): "Топологічний Шлях",
        ('*', (
            "Color of paths which uses topology calculation method"
        )): (
            "Колір шляху що використовує топологічний метод обрахування"
        ),
        ('Preferences', "Active Path"): "Активний Шлях",
        ('*', "Active path color"): "Колір активного шляху",
        ('Preferences', "Active Topology Path"): "Активний Топологічний Шлях",
        ('*', (
            "Color of active path which uses topology calculation method"
        )): (
            "Колір активного шляху що використовує топологічний метод обрахування"
        ),
        ('Preferences', "Path Behind Mesh"): "Шлях За Сіткою",
        ('*', "The color of the path displayed behind the mesh"): "Колір шляху відображеного за сіткою об'єкту",
        ('Preferences', "Vertex Size"): "Розмір Вершин",
        ('*', (
            "The size of the vertex that represents the control element"
        )): (
            "Розмір вершини яка позначає контрольний елемент"
        ),
        ('Preferences', "Edge Width"): "Товщина Ліній",
        ('*', "Line Thickness"): "Товщина Ліній",
        ('*', (
            "The thickness of the lines that mark the segments of the path"
        )): (
            "Товщина ліній які позначають відрізки шляху"
        ),

        ('Preferences', "Auto Tweak Options"): "Автоматичне Корегування Опцій",
        ('*', (
            "Adjust operator options. If no mesh element is initially selected, the selection option will be changed "
            "to \"Extend\". If all elements are selected, it will be changed to \"Do nothing\"")
         ): (
            "Вносити корективи до опцій. Якщо на початку роботи не виділено нічого, буде змінено опцію виділення на"
            "\"Розширення\". Якщо ж виділено все - на \"Нічого не робити\""
        ),

        ('Preferences', "How To Use the Addon"): "Як Користуватися Доповненням",
        ('Preferences', "License"): "Ліцензія",
        ('Preferences', "Links"): "Посилання",
        # ---

        # Рядки містяться в усіх властивостях (mark_select, mark_seam, mark_sharp)
        ('WMProps', "Do nothing"): "Нічого не робити",
        ('*', "Do nothing"): "Нічого не робити",

        # Рядки містяться у властивостях mark_seam, mark_sharp
        ('WMProps', "Mark"): "Позначити",
        ('WMProps', "Clear"): "Очистити",
        ('WMProps', "Toggle"): "Інвертувати",

        # Виділення
        ('WMProps', "Select"): "Виділення",
        ('*', "Selection options"): "Опції виділення",

        ('WMProps', "Extend"): "Розширити",
        ('*', "Extend existing selection"): "Розширити наявне виділення",
        ('WMProps', "Subtract"): "Відняти",
        ('*', "Subtract existing selection"): "Зняти виділення з наявного",
        ('WMProps', "Invert"): "Інвертувати",
        ('*', "Inverts existing selection"): "Інвертувати наявне виділення",

        # Шов
        ('WMProps', "Seam"): "Шов",
        ('*', "Mark seam options"): "Опції позначення швів",

        ('*', "Mark seam path elements"): "Позначити елементи шляху(ів) як шви",
        ('*', "Clear seam path elements"): "Очистити позначені шви елементами шляху(ів)",
        ('*', "Toggle seams on path elements"): "Інвертувати позначення швів елементами шляху(ів)",

        # Гострота
        ('WMProps', "Sharp"): "Гострота",
        ('*', "Mark sharp options"): "Опції гостроти",

        ('*', "Mark sharp path elements"): "Позначити елементи шляху(ів) як гострі",
        ('*', "Clear sharp path elements"): "Позначити елементи шляху(ів) як тупі",
        ('*', "Toggle sharpness on path"): "Інвертувати позначену гостроту елементами шляху(ів)",

        # Топологічна Відстань
        ('WMProps', "Use Topology Distance"): "Топологічна Відстань",
        ('*', (
            "Use the algorithm for determining the shortest path without taking into account the spatial distance, "
            "only the number of steps. Newly created paths will use the value of the option, but this can be adjusted "
            "individually for each of them"
        )
        ): (
            "Використовувати алгоритм визначення найкоротшого шляху без урахування просторової відстані, лише "
            "кількості кроків. Новоутворені шляхи будуть використовувати значення опції, але це можна корегувати "
            "індивідуально для кожного з них"
        ),

        # Шлях за сіткою об'єкту
        ('WMProps', "Show Path Behind"): "Показувати Шлях за Сіткою",
        ('*', "Whether to show the path behind the mesh"): "Чи показувати шлях що знаходиться за сіткою об'єкту",

        # Основний оператор.
        ('MESH_OT_select_path', "Select Path"): "Виділення Шляху",
        ('MESH_OT_select_path', "Add New Control Point"): "Створити Контрольний Елемент",
        ('MESH_OT_select_path', "Add New Path"): "Створити Новий Шлях",
        ('MESH_OT_select_path', "Remove Control Point"): "Усунути Контрольний Елемент",
        ('MESH_OT_select_path', "Drag Control Point"): "Перетягнути Контрольний Елемент",
        ('MESH_OT_select_path', "Release Path"): "Відпустити Шлях",
        ('MESH_OT_select_path', "Open Pie Menu"): "Відкрити Кругове Меню",

        ('MESH_OT_select_path', "Direction"): "Розвернути",
        ('*', (
            "Change the direction of the active path.\n"
            "The active element of the path will be the final element "
            "from the opposite end of the path, from it will be formed a section to the next control element that "
            "you create."
        )
        ): (
            "Змінити напрямок активного шляху.\n"
            "Активним стане останній елемент шляху з протилежного кінця, від нього будуть утворюватися нові секції до "
            "новостворених елементів"
        ),

        ('MESH_OT_select_path', "Close Path"): "Замкнути",
        ('*', "Connect the start and end of the active path"): "З'єднати початок і кінець активного шляху",

        ('MESH_OT_select_path', "Cancel"): "Припинити",
        ('*', "Cancel editing paths"): "Припинити роботу зі шляхами",

        ('MESH_OT_select_path', "Apply"): "Застосувати",
        ('*', (
            "Apply changes to the grid according to the selected options"
        )): (
            "Застосувати зміни до сітки відповідно "
            "до обраних опцій"
        ),

        ('MESH_OT_select_path', "Undo"): "Повернути",
        ('*', "Take a step back"): "Скасувати останню дію",

        ('MESH_OT_select_path', "Redo"): "Повторити",
        ('*', "Redo previous undo"): "Відновити скасовану дію",

        ('MESH_OT_select_path', "Topology"): "Топологія",
        ('*', (
            "Algorithm for determining the shortest path without taking into account the spatial distance, only the "
            "number of steps"
        )): (
            "Алгоритм визначення найкоротшого шляху без урахування просторової відстані, лише кількості кроків"
        ),

        ('MESH_PT_select_path_context', "Options"): "Параметри",
        ('WMProps', "Tool Settings"): "Параметри Інструменту",

        # Попередні Налаштування.
        ('*', "Load a preset"): "Обрати попереднє налаштування",
        ('*', "Appearance Preset"): "Шаблон Відображення",
        ('PREFERENCES_OT_path_tool_appearance_preset', "Add preset"): "Створити шаблон відображення",
        ('PREFERENCES_OT_path_tool_appearance_preset', "Remove preset"): "Усунути шаблон відображення",
        ('*', "Operator Preset"): "Шаблон Оператора",
        ('MESH_OT_select_path_preset_add', "Add preset"): "Створити шаблон оператора",
        ('MESH_OT_select_path_preset_add', "Remove preset"): "Усунути шаблон оператора",


        # BHQAB_Preferences.
        ('BHQAB_Preferences', "AA Method"): "Метод Згладжування",
        ('*', "Anti-aliasing method to be used"): "Який метод згладжування використовувати",

        ('BHQAB_Preferences', "Preset"): "Попередні Налаштування",

        ('BHQAB_Preferences', "None"): "Вимкнено",
        ('BHQAB_Preferences', "Low"): "Низькі",
        ('BHQAB_Preferences', "Medium"): "Середні",
        ('BHQAB_Preferences', "High"): "Високі",
        ('BHQAB_Preferences', "Ultra"): "Найвищі",

        ('*', "Fast approximate anti-aliasing"): "Швидке спрощене згладжування",

        ('BHQAB_Preferences', "Quality"): "Якість",
        ('*', "FXAA preset quality tuning"): "Більш точне налаштування якості обраного попереднього налаштування",

        ('*', "Sub-pixel morphological anti-aliasing"): "Субпіксельне морфологічне згладжування",
        ('*', "Sub-pixel morphological anti-aliasing quality preset"): (
            "Попереднє налаштування субпіксельного морфологічного згладжування"
        ),

        ('*', "Fast approximate anti-aliasing quality preset"): (
            "Попереднє налаштування швидкого спрощеного згладжування"
        ),

        ('*', "Do not use fast approximate anti-aliasing"): "Не використовувати швидке спрощене згладжування",
        ('*', "Default medium dither"): "Середній рівень дитерингу",
        ('*', "Less dither, faster"): "Зменшений рівень дитерингу, швидша обробка",
        ('*', "Less dither, more expensive"): "Зменшений рівень дитерингу, використовує більше ресурсів",
        ('*', "No dither, very expensive"): "Без дитерингу, використовує найбільшу кількість ресурсів",

        ('*', "Do not use sub-pixel morphological anti-aliasing"): (
            "Не використовувати субпіксельне морфологічне згладжування"
        ),
        ('*', ("60% of the quality. High threshold, very a few search steps, no detection of corners and "
               "diagonals")): (
                   "60% якості. Високий поріг, мала кількість кроків пошуку, відсутнє виявлення кутів і діагоналей"
        ),
        ('*', "80% of the quality. Medium threshold, few search steps, no detection of corners and diagonals"): (
            "80% якості. Середній поріг, невелика кількість кроків пошуку, відсутнє виявлення кутів і діагоналей"
        ),
        ('*', "95% of the quality. Medium threshold, more search steps, detection of corners and diagonals"): (
            "95% якості. Середній поріг, більша кількість кроків пошуку, виявлення кутів і діагоналей"
        ),
        ('*', "99% of the quality. A lot of search steps, diagonal and corner search steps, lowest threshold"): (
            "99% якості. Велика кількість кроків пошуку, виявлення кутів і діагоналей, найнижчий поріг"
        ),

    },
}
