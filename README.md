# Path Tool

- [Path Tool](#path-tool)
  - [About](#about)
  - [How To Use the Addon](#how-to-use-the-addon)
  - [Release Notes](#release-notes)
  - [License](#license)

## About

An add-on for Blender that complements the standard shortcut operator with new features.

The standard operator works great, but in terms of user experience, it could be better. Of course, most Blender operators work on the principle of "here and now", but for real work tasks this operator is used, including for marking UV seams, highlighting faces for sharp shading, highlighting a line along the mesh object to divide it into parts, etc. The bottom line is that in terms of user experience, we first select some mesh elements, then perform some operation with them.

This addon is designed taking into account many points concerning the actual use of it in work tasks. The initial idea is quite simple - the operation of selecting the shortest path should be similar to working with the "Knife" tool.

![Path Tool](https://github.com/BlenderHQ/path_tool/assets/16822993/c3d6947e-31bf-4da5-84ab-73f3952e8c40)

## How To Use the Addon

After installing the add-on, the "Select Path" tool will appear next to the standard mesh element selection tools ("Tweak", "Select Box", ...). Next, you can start working with one or more objects in mesh editing mode.
    
Again (we won't mention this later, just keep in mind that this is done for the same purpose), considering the user experience, mesh element selection is done in two modes:

* Selection of edges:

    * Work in this mode will start only if there are no faces in the selection mode. In this case, the selection mode will be changed to edges as soon as the first control element is selected.

    * Mesh vertices are control points.

* Selection of faces:

    * Work in this will start if there are faces in the selection mode. In this case, the selection mode will be changed only on the face, as soon as the first control element is selected.

    * Mesh edges in this case are control points.

Vertex selection mode makes no sense because it is completely overridden by edge selection mode.

So, you have chosen a tool, decided in which mode you will edit the selection, created the first control element.

When you click on the next mesh element, a new path control element will be created and the shortest path will be built between it and the previous one. The newly created control element will become active.

Next, we will call the set of control elements and segments between them simply "Path".

So, we have the first path.
At work, it is sometimes necessary to replace the active element from the end to the beginning, for this there is an option in the circular menu or a keyboard shortcut. You can move the control element and the corresponding path segments will be rebuilt. If you need to close the gap between the first and last control element, you can also use the corresponding option in the circular menu or keyboard shortcut.

Multi-path work is also supported. You can use a keyboard shortcut to create a new path. When you do this, a new control element will be created, independent of the previous path, and work will continue in a familiar way.

There are also several interesting points - different paths can interact. If you move a control at the beginning or end of one path to the beginning or end of another path, these paths will merge into one. If one of the control elements is not an endpoint, then the paths will not be joined. Instead, the controls will stick together and can be moved at the same time.
    
---

## Release Notes

<details open><summary>
<b>Version 3.6.2</b>
</summary>

* Fixed an issue with flipped normals in the viewport. #5

* Updated the shader system to the new Blender development design standards (maintenance update).

* Fixed an issue with control point opacity in edge mode.

* Increased accuracy of depth and color to 32-bit float - this reduces polygon depth fighting in the viewport.

* Fixed different distance between "Select", "Seam", "Sharp" options in tool settings and radial menu.

* Brought back module reload support.

* Added localization support, with initial `uk_UA` translations. Users can create their own translations in other languages ​​using fields from this dictionary.

* Now, while working with paths, the addon's UI will become inactive, as access to it is not possible at this time and this should be reflected in the UI. This also applies to keymap preferences.
</details>


<details><summary>
<b>Version 3.4.1</b>
</summary>

* Added "Auto Tweak Options" preferences option. This used to be the operator's default behavior for ease of use, but is now optional and disabled by default. If no mesh element is initially selected, the selection option will be changed to "Extend". If all elements are selected, it will be changed to "Do nothing". The option is in the addon preferences under `Behavior > Auto Tweak Options`.

* Main operator has been fixed in a situation where you do undo and redo and then cancel the operator, after which start a new instance of the operator again

* Added a system of keyboard shortcuts that were previously hardcoded. All of them are available in user preferences. Here, Blender has limitations because it does not provide any possibility to create keymaps for modal operators through the Python API. Among the identified shortcomings (however, they were there before) - it is not possible to assign "Double Click" and "Click-and-Drag" actions to the keys.

* Standard settings that simplify navigation - "Auto Perspective" and "Zoom to Mouse Position" have been added to the behavior settings. This is useful for faster setup.
</details>


<details><summary>
<b>Version 3.4.0</b>
</summary>

* Fixed selection for meshes with glued geometry. The problem was how the standard `bpy.ops.mesh.select_linked` operator works, which selects part of the mesh according to normals. The simplest example to reproduce is two pyramids glued together with their upper faces cut off.

* Brought back transparency options for drawing paths and their controls.
</details>


<details><summary>
<b>Version 3.3.0</b>
</summary>

* Fixed possible Blender crashes when changing the anti-aliasing method. The reason was how Blender calculates VAO.

* Fixed incomplete selection of mesh elements when working with edges. The reason was the absence of one of the mesh update calls.

* Fixed the incorrect merging of paths in the case when they are connected to the first control element of the first path with the first control element of the second path. The reason was a typo in determining element indexes.

* Fixed lags when dragging control elements on Linux (tested on Ubuntu). The problem was in the spam of `INBETWEEN_MOUSEMOVE` events by Blender.

* Removed the "Default presets" option from the preferences. Added a completely new system of presets. The new system is more maintainable and native to Blender. Appearance presets have also been added.

</details>


<details><summary>
<b>Version 3.2.0</b>
</summary>

* Added support for work in all view-ports as well as in all open Blender windows - now there is no binding to a specific viewport in the specific window in which the work was started.

* Added support for anti-aliasing FXAA, SMAA, with configurable options. They are performed sequentially - that is, you can enable only some of these methods for finer tuning on your hardware.

* Changes to the operation logic of operator properties:
    
    * Added operator presets.

    * The option to apply options to tool properties has been removed - now the tool properties and the properties of the current operator session are combined.

    * Options in the pie menu reflect actions for the current path of the operator - it can be reversed, closed, etc. but operator options and access to addon preferences are in a separate submenu. An important change is that now it will not disappear after each tweak of the options.

* Added option from standard operator "Topology distance". It can be enabled for each individual path and enabled by default for all new ones in the operator / tool options.

</details>

## License

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue)](https://www.gnu.org/licenses/gpl-3.0)

Copyright © 2020-2023 Vlad Kuzmin (ssh4), Ivan Perevala (ivpe).

<details><summary>
GNU GPL v3 License.
</summary>

```
Path Tool addon.
Copyright (C) 2020-2023 Vlad Kuzmin (ssh4), Ivan Perevala (ivpe)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
```

</details>