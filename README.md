# Path Tool
Multi purpose Blender 2.8x addon for selecting and marking up mesh object elements.
There is support for working simultaneously with multiple objects in edit mode. Installation is standard for Blender (Go to `Edit > Preferences > Addons > Install` and select the downloaded archive). Select one or more meshes and go into edit mode. In the toolbar, select Path Tool.

## Mesh elements selection
Work with the tool is carried out in the mode of selecting edges or faces. For the convenience of working with the mesh edges, vertices are used as control elements

## Path editing
Control elements of active path (the last one you interacted with) can be added (`LMB` on mesh), moved (`LMB` on element you want to move and drag) and removed (`Ctrl + LMB`). To start a new path otherwise existing one, click `Shift + LMB`. When you finished active path, it can be closed from first to last control element (`RMB` to open pie menu and select `Close Path`). Also if you just closed active path, next click on mesh element not related to any existing path will create a new path too. Control elements can be added after last element of active path and on existing segment between pair of other control elements. To add control element at start of active path, switch direction of path (`RMB` to open pie menu and select `Change direction`).

When you move control element of path to adjacent of the same path, they are joined, otherwise elements are not adjacent it will just moved. If you move first-to-last element of the same path, path will be closed.
Pathes can interact each other. If you drag endpoint of one path to endpoint of other, two pathes will be joined. Also, if the controls are not endpoints, after releasing the drag and drop, they stick together when dragging.

## Compatibility
The addon supports older Blender versions as well as the newest ones. Please, note that for compatibility reasons with newest Blender versions we may stop support of older Blender versions. All this statements are caused by testing existing and new features of the addon in every official Blender release. As a rule, most of issues are well handled in Blender LTS releases (Blender 2.83 is the first LTS release), so we try to keep their support as long as Blender Foundation supports this releases.

A long story short, minimal supported Blender version means that if you install the addon on earlier version of Blender - you would get just warning message in addon user preferences, no any new functionalities would be added. But you may try to install the addon on newest Blender version, for example, on alpha or daily builds of Blender. This releases can not be completely tested, so you do this on your own risk. Of course, every new official release of Blender would be tested as fast as possible.

Also note that for now, addon version always equals to latest tested Blender version.

## License
The addon uses GNU General Public License v3, which means that its free. Copy of the license you can  find inside this repository (at `./LICENSE` file).