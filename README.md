# Path Tool

An add-on for Blender that complements the standard shortcut operator with new features.

The standard operator works great, but in terms of user experience, it could be better. Of course, most Blender operators work on the principle of "here and now", but for real work tasks this operator is used, including for marking UV seams, highlighting faces for sharp shading, highlighting a line along the mesh object to divide it into parts, etc. The bottom line is that in terms of user experience, we first select some mesh elements, then perform some operation with them.

This addon is designed taking into account many points concerning the actual use of it in work tasks. The initial idea is quite simple - the operation of selecting the shortest path should be similar to working with the "Knife" tool.

---

# Release Notes

## Version 3.3.0
* Fixed possible Blender crashes when changing the anti-aliasing method. The reason was how Blender calculates VAO.

* Fixed incomplete selection of mesh elements when working with edges. The reason was the absence of one of the mesh update calls.

* Fixed the incorrect merging of paths in the case when they are connected to the first control element of the first path with the first control element of the second path. The reason was a typo in determining element indexes.

* Fixed lags when dragging control elements on Linux (tested on Ubuntu). The problem was in the spam of `INBETWEEN_MOUSEMOVE` events by Blender.

* Removed the "Default presets" option from the preferences. Added a completely new system of presets. The new system is more maintainable and native to Blender. Appearance presets have also been added.


## Version 3.2.0

* Added support for work in all view-ports as well as in all open Blender windows - now there is no binding to a specific viewport in the specific window in which the work was started.

* Added support for anti-aliasing SSAA, FXAA, SMAA, with configurable options. They are performed sequentially - that is, you can enable only some of these methods for finer tuning on your hardware.

* Changes to the operation logic of operator properties:
    
    * Added operator presets.

    * The option to apply options to tool properties has been removed - now the tool properties and the properties of the current operator session are combined.

    * Options in the pie menu reflect actions for the current path of the operator - it can be reversed, closed, etc. but operator options and access to addon preferences are in a separate submenu. An important change is that now it will not disappear after each tweak of the options.

* Added option from standard operator "Topology distance". It can be enabled for each individual path and enabled by default for all new ones in the operator / tool options.

# How To Use the Addon

After installing the addon, next to the standard tools for selecting mesh elements ("Tweak", "Select Box", ...) will appear "Select Path" tool.

Keep in mind that working with multiple mesh objects in edit mode is supported, let's move on to the basics.

Again (we will not mention this later, just keep in mind that this is done for the same purpose), taking into account the user experience, the selection of mesh elements is carried out in two modes of the operator:

* Selection of **edges**:

    * Work in this mode will start if there are no faces in the selection tool mode. In this case, the selection mode will be switched to edge only when the first control element is selected.

    * Mesh vertices act as control points to build a path between them

* Selection of **faces**:
    
    * Work in this mode will be started if faces are present in the selection tool mode. In this case, the selection mode will be switched to only the faces when the first control element is selected.

    * The faces of the mesh in this case act as control points to build a path between them

The vertex selection mode is skipped because it completely overlaps the edge selection mode.

So, you have chosen the tool, you have decided in what mode you will edit the selection, you have created the first control element.

When you click on the next mesh element, a new control element will be added and a short path will be built between them. The newly created control will become active. For simplicity of the story - a set of control elements and the paths between them will be called simply "Path". So, we have the first Path. In the work sometimes it is necessary to swap the active element from end to beginning, for this you have an option in the pie menu or shortcut displayed in the status bar. You can move the control elements of the path and it will be rebuilt. If you need to close the gap between the first and last Path's control, you also can use the appropriate option in the Pie menu or shortcut displayed in the status bar.

Work with several Path's is also supported. To create a new Path, you can use the shortcut displayed in the status bar. When you do this, a new control element independent of the first Path will be created and the work will continue in the already familiar way.

There are also some interesting points - different Paths can interact. If the control at the beginning or end of one Path is moved to the beginning or end of another Path, these Paths will merge into one. If the control is not finite then the paths will not be merged. Instead, all the control elements of all the paths that are on the same element of the mesh, in the same place, can be moved together, they seem to stick together
