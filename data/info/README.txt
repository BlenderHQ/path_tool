How to use the add-on:

After installing the add-on, the "Select Path" tool will appear next to the standard mesh element selection tools ("Tweak", "Select Box", ...). Next, you can start working with one or more objects in mesh editing mode.
    
Again (we won't mention this later, just keep in mind that this is done for the same purpose), considering the user experience, mesh element selection is done in two modes:

• Selection of edges:

      ° Work in this mode will start only if there are no faces in the selection mode. In this case, the selection mode will be changed to edges as soon as the first control element is selected.

      ° Mesh vertices are control points.

• Selection of faces:

      ° Work in this will start if there are faces in the selection mode. In this case, the selection mode will be changed only on the face, as soon as the first control element is selected.

      ° Mesh edges in this case are control points.

Vertex selection mode makes no sense because it is completely overridden by edge selection mode.

So, you have chosen a tool, decided in which mode you will edit the selection, created the first control element.

When you click on the next mesh element, a new path control element will be created and the shortest path will be built between it and the previous one. The newly created control element will become active.

Next, we will call the set of control elements and segments between them simply "Path".

So, we have the first path.
At work, it is sometimes necessary to replace the active element from the end to the beginning, for this there is an option in the circular menu or a keyboard shortcut. You can move the control element and the corresponding path segments will be rebuilt. If you need to close the gap between the first and last control element, you can also use the corresponding option in the circular menu or keyboard shortcut.

Multi-path work is also supported. You can use a keyboard shortcut to create a new path. When you do this, a new control element will be created, independent of the previous path, and work will continue in a familiar way.

There are also several interesting points - different paths can interact. If you move a control at the beginning or end of one path to the beginning or end of another path, these paths will merge into one. If one of the control elements is not an endpoint, then the paths will not be joined. Instead, the controls will stick together and can be moved at the same time.
    
😊 I hope someone needs this explanation. I wish you a good day at work filled with new opportunities and exciting times!