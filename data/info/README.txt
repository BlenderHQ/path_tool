How To Use the Addon:

After installing the addon, next to the standard tools for selecting mesh elements ("Tweak", "Select Box", ...) will appear "Select Path" tool.
Keep in mind that working with multiple mesh objects in edit mode is supported, let's move on to the basics.
Again (we will not mention this later, just keep in mind that this is done for the same purpose), taking into account the user experience, the selection of mesh elements is carried out in two modes of the operator:

Selection of edges:
    - Work in this mode will start if there are no faces in the selection tool mode. In this case, the selection mode will be switched to edge only when the first control element is selected.
    - Mesh vertices act as control points to build a path between them

Selection of faces:
    - Work in this mode will be started if faces are present in the selection tool mode. In this case, the selection mode will be switched to only the faces when the first control element is selected.
    - The faces of the mesh in this case act as control points to build a path between them

The vertex selection mode is skipped because it completely overlaps the edge selection mode.
So, you have chosen the tool, you have decided in what mode you will edit the selection, you have created the first control element.

When you click on the next mesh element, a new control element will be added and a short path will be built between them. The newly created control will become active. For simplicity of the story - a set of control elements and the paths between them will be called simply "Path". So, we have the first Path. In the work sometimes it is necessary to swap the active element from end to beginning, for this you have an option in the pie menu or shortcut displayed in the status bar. You can move the control elements of the path and it will be rebuilt. If you need to close the gap between the first and last Path's control, you also can use the appropriate option in the Pie menu or shortcut displayed in the status bar.

Work with several Path's is also supported. To create a new Path, you can use the shortcut displayed in the status bar. When you do this, a new control element independent of the first Path will be created and the work will continue in the already familiar way.

There are also some interesting points - different Paths can interact. If the control at the beginning or end of one Path is moved to the beginning or end of another Path, these Paths will merge into one. If the control is not finite then the paths will not be merged. Instead, all the control elements of all the paths that are on the same element of the mesh, in the same place, can be moved together, they seem to stick together
