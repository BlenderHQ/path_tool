# Path Tool
Multi purpose Blender 2.8x addon for selecting and marking up mesh object elements.
There is support for working simultaneously with multiple objects in edit mode.

# Installation
Installation is standard for Blender (Go to `Edit > Preferences > Addons > Install` and select the downloaded archive).

# Quick Guide
So, after installing the addon, you can get to work. To do this, select one or more meshes and go into edit mode. In the toolbar, select the Path Tool.
* **Mesh elements selection.** 
Work with the tool is carried out in the mode of selecting edges or faces. For the convenience of working with the mesh edges, vertices are used as control elements
* **Path editing.**

For now the addon has support of multiple path editing. Control elements of active path (the last one you interacted with) can be added (`LMB` on mesh), moved (`LMB` on element you want to move + `Drag`) and removed (`Ctrl + LMB`). To start a new path otherwise existing one, click `Shift + LMB`. Also if you just closed active path, next click on mesh will create a new path too. Control elements can be added after last added control element of active path and on existing segment between pair of other control elements. To add control element at start of active path, switch direction of path (`RMB` to open pie menu and select `Change direction`)
