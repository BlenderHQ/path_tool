# Path Tool

Переглянути
[🇺🇸](./README.md),
[🇺🇦](./README_uk.md)
.

- [Path Tool](#path-tool)
  - [Опис](#опис)
  - [Як Використовувати Доповнення](#як-використовувати-доповнення)
  - [Нотатки щодо Випусків](#нотатки-щодо-випусків)
  - [Ліцензія](#ліцензія)

## Опис

Доповнення для Blender що доповнює стандартний оператор вибору найкоротшого шляху.

Стандартний оператор працює чудово, але з точки зору користувацького досвіду може бути краще. Звісно, більшість операторів Blender працюють за принципом "тут і зараз" але для реальних робочих завдань, включно з позначенням UV швів, ребер що повинні бути гострими, вибором лінії вздовж сітки об'єкта для того щоб поділити його на частини, тощо, цього не достатньо.

Це доповнення спроектовано зважаючи на більшість ключових способів використання в робочих завданнях. Початкова ідея доволі проста - виділення найкоротшого шляху повинно бути схожим на роботу з інструментом "Ніж".

![Path Tool](https://github.com/BlenderHQ/path_tool/assets/16822993/c3d6947e-31bf-4da5-84ab-73f3952e8c40)

## Як Використовувати Доповнення

Після встановлення доповнення поряд зі стандартними інструментами виділення елементів сітки ("Tweak", "Select Box", ...) з’явиться інструмент "Select Path". Далі можна починати працювати з одним або кількома об'єктами у режимі редагування сітки.
    
Знову ж таки (не будемо згадувати про це пізніше, тільки майте на увазі, що це робиться з тією ж метою), враховуючи користувацький досвід, вибір елементів сітки здійснюється в двох режимах:

• Вибір ребер:

     ° Робота в цьому режимі почнеться, лиш тоді якщо в режимі вибору немає граней. У цьому випадку режим виділення буде змінено на ребра тільки-но буде обрано перший контрольний елемент.

     ° Вершини сітки є контрольними точками.

• Вибір граней:

     ° Робота в цьому почнеться, якщо в режимі вибору присутні грані. У цьому випадку режим виділення буде змінено лише на грані, тільки-но буде виділено перший контрольний елемент.

     ° Грані сітки в цьому випадку є контрольними точками.

Режим виділення вершин не має сенсу, оскільки його повністю перекриває режим виділення ребер.

Отже, ви вибрали інструмент, вирішили, в якому режимі будете редагувати виділення, створили перший контрольний елемент.

Коли ви натискаєте на наступний елемент сітки, буде створено новий контрольний елемент шляху, а між ним і попереднім буде побудовано найкоротший шлях. Новостворений контрольний елемент стане активним.

Далі - набір контрольних елементів і відрізків між ними будемо називати просто "Шлях".

Отже, маємо перший шлях.
У роботі інколи виникає необхідність замінити активний елемент з кінця на початок, для цього є опція в круговому меню або клавіатурне скорочення. Можна перемістити контрольний елемент і відповідні сегменти шляху буде перебудовано. Якщо потрібно закрити проміжок між першим і останнім контрольним елементом, також можете скористатися відповідним параметром у круговому меню або клавіатурним скороченням.

Також підтримується робота з кількома шляхами. Щоб створити новий шлях, ви можете скористатися клавіатурним скороченням. Коли ви це зробите, буде створено новий контрольний елемент, незалежний від попереднього шляху, і робота продовжиться вже у знайомий спосіб.

Також є кілька цікавих моментів - різні шляхи можуть взаємодіяти. Якщо контрольний елемент на початку або в кінці одного шляху перемістити на початок або кінець іншого шляху, ці шляхи об’єднаються в один. Якщо один з контрольних елементів не крайній, то шляхи не буде об'єднано. Натомість контрольні елементи злипнуться і їх можна буде перемістити одночасно.

---

## Нотатки щодо Випусків

<details open><summary>
<b>Версія 4.0.0</b>
</summary>

* Оновлено систему випуску доповнення.

* Додано опцію для відображення шляху за сіткою об'єкту.

* Додано косметичні зміни до користувацького інтерфейсу.

* Додано нову систему перевірки і встановлення оновлень.

</details>

<details><summary>
<b>Версія 3.6.2</b>
</summary>

• Виправлено неполадку стосовно вивернутих нормалей у вікні перегляду.

• Оновлено систему шейдерів до нових стандартів розробки Blender (технічне оновлення).

• Виправлено неполадку стосовно прозорості контрольних елементів у режимі редагування ребер.

• Підвищено точність текстур глибини і кольору до 32-бітної - це зменшує можливість некоректного відображення елементів у переглядачі.

• Виправлено неполадку стосовно різної відстані між опціями "Виділення", "Шов" і "Гострота" в налаштуваннях інструменту і круговому меню.

• Повернено підтримку перезавантаження модуля.

• Додано підтримку локалізації інтерфейсу, для початку `uk_UA`. Користувачі можуть створювати власні переклади їх мовами використовуючи поля з цього словника як шаблон.

• Тепер під час роботи користувацький інтерфейс ставатиме неактивним, оскільки доступ до нього обмежено і це повинно бути відображено. Це стосується і налаштувань клавіш.
</details>


<details><summary>
<b>Версія 3.4.1</b>
</summary>

* Added "Auto Tweak Options" preferences option. This used to be the operator's default behavior for ease of use, but is now optional and disabled by default. If no mesh element is initially selected, the selection option will be changed to "Extend". If all elements are selected, it will be changed to "Do nothing". The option is in the addon preferences under `Behavior > Auto Tweak Options`.

* Main operator has been fixed in a situation where you do undo and redo and then cancel the operator, after which start a new instance of the operator again

* Added a system of keyboard shortcuts that were previously hardcoded. All of them are available in user preferences. Here, Blender has limitations because it does not provide any possibility to create keymaps for modal operators through the Python API. Among the identified shortcomings (however, they were there before) - it is not possible to assign "Double Click" and "Click-and-Drag" actions to the keys.

* Standard settings that simplify navigation - "Auto Perspective" and "Zoom to Mouse Position" have been added to the behavior settings. This is useful for faster setup.
</details>


<details><summary>
<b>Версія 3.4.0</b>
</summary>

* Fixed selection for meshes with glued geometry. The problem was how the standard `bpy.ops.mesh.select_linked` operator works, which selects part of the mesh according to normals. The simplest example to reproduce is two pyramids glued together with their upper faces cut off.

* Brought back transparency options for drawing paths and their controls.
</details>


<details><summary>
<b>Версія 3.3.0</b>
</summary>

* Fixed possible Blender crashes when changing the anti-aliasing method. The reason was how Blender calculates VAO.

* Fixed incomplete selection of mesh elements when working with edges. The reason was the absence of one of the mesh update calls.

* Fixed the incorrect merging of paths in the case when they are connected to the first control element of the first path with the first control element of the second path. The reason was a typo in determining element indexes.

* Fixed lags when dragging control elements on Linux (tested on Ubuntu). The problem was in the spam of `INBETWEEN_MOUSEMOVE` events by Blender.

* Removed the "Default presets" option from the preferences. Added a completely new system of presets. The new system is more maintainable and native to Blender. Appearance presets have also been added.

</details>


<details><summary>
<b>Версія 3.2.0</b>
</summary>

* Added support for work in all view-ports as well as in all open Blender windows - now there is no binding to a specific viewport in the specific window in which the work was started.

* Added support for anti-aliasing FXAA, SMAA, with configurable options. They are performed sequentially - that is, you can enable only some of these methods for finer tuning on your hardware.

* Changes to the operation logic of operator properties:
    
    * Added operator presets.

    * The option to apply options to tool properties has been removed - now the tool properties and the properties of the current operator session are combined.

    * Options in the pie menu reflect actions for the current path of the operator - it can be reversed, closed, etc. but operator options and access to addon preferences are in a separate submenu. An important change is that now it will not disappear after each tweak of the options.

* Added option from standard operator "Topology distance". It can be enabled for each individual path and enabled by default for all new ones in the operator / tool options.

</details>

## Ліцензія

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue)](https://www.gnu.org/licenses/gpl-3.0)

Копірайт © 2020 Vladlen Kuzmin (ssh4), Ivan Perevala (ivpe).

<details><summary>
Ліцензія GNU GPL v3.
</summary>

```
Доповнення Path Tool для Blender.
Копірайт © 2020 Владлен Кузьмін (ssh4), Іван Перевала (ivpe)

Ця програма — вільне програмне забезпечення: Ви можете розповсюджувати
її та/або вносити зміни відповідно до умов Загальної Публічної
Ліцензії GNU у тому вигляді, у якому вона була опублікована Фундацією
Вільного Програмного Забезпечення, або 3-ї версії Ліцензії, або (на Ваш
розсуд) будь-якої більш пізньої версії.

Ця програма розповсюджується із сподіванням, що вона виявиться
корисною, але БЕЗ БУДЬ-ЯКОЇ ҐАРАНТІЇ, без навіть УЯВНОЇ ҐАРАНТІЇ
КОМЕРЦІЙНОЇ ПРИДАТНОСТІ чи ВІДПОВІДНОСТІ БУДЬ-ЯКОМУ ПЕВНОМУ
ЗАСТОСУВАННЮ. Зверніться до Загальної Публічної Ліцензії GNU за
подробицями.

Ви мали отримати копію Загальної Публічної Ліцензії GNU разом з цією
програмою. Якщо Ви не отримали копії ліцензії, перегляньте
<https://www.gnu.org/licenses/>.
```

Це — неофіційний переклад Загальної Публічної Ліцензії GNU (GNU General Public License, GNU GPL) українською мовою. Цей переклад не був опублікований Фундацією Вільного програмного забезпечення і не встановлює ніяких законодавчих умов щодо розповсюдження програмного забезпечення з використанням GNU GPL. Тільки ориґінальна англійська версія встановлює такі умови. Однак, ми сподіваємось, що цей переклад допоможе україномовним користувачам краще зрозуміти GNU GPL.


</details>
