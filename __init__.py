_D='LEFTMOUSE'
_C=True
_B='action'
_A='PRESS'
bl_info={'name':'Path Tool 4.0.1','author':'Vladlen Kuzmin (ssh4), Ivan Perevala (ivpe)','version':(4,0,1),'blender':(4,0,0),'location':'Toolbar','description':'Tool for selecting and marking up mesh object elements','category':'Mesh','support':'COMMUNITY','doc_url':'https://github.com/BlenderHQ/path-tool'}
import os
from.lib import bhqab
ADDON_PKG=bhqab.utils_ui.get_addon_package_name()
DATA_DIR=os.path.join(os.path.dirname(__file__),'data')
INFO_DIR=os.path.join(DATA_DIR,'info')
if'bpy'in locals():from importlib import reload;reload(bhqab);reload(bhqglsl);reload(bhqupd);reload(pref);reload(main);reload(props);reload(langs);reload(icons)
else:from.lib import bhqab,bhqglsl,bhqupd;from.import pref;from.import main;from.import props;from.import langs;from.import icons
import bpy
from bpy.types import Context,UILayout,WindowManager,WorkSpaceTool
from bpy.props import PointerProperty
from bpy.app.handlers import persistent
from typing import TYPE_CHECKING
if TYPE_CHECKING:from.props import WMProps
class PathToolMesh(WorkSpaceTool):
	bl_idname='mesh.path_tool';bl_label='Select Path';bl_space_type='VIEW_3D';bl_context_mode='EDIT_MESH';bl_options={};bl_description='Select items using editable paths';bl_icon=os.path.join(DATA_DIR,'icons','ops.mesh.path_tool');bl_keymap=(main.MESH_OT_select_path.bl_idname,dict(type=_D,value=_A,shift=_C),dict(properties=[(_B,main.InteractEvent.ADD_NEW_PATH.name)])),(main.MESH_OT_select_path.bl_idname,dict(type=_D,value=_A,ctrl=_C),dict(properties=[(_B,main.InteractEvent.REMOVE_CP.name)])),(main.MESH_OT_select_path.bl_idname,dict(type='T',value=_A),dict(properties=[(_B,main.InteractEvent.TOPOLOGY_DISTANCE.name)])),(main.MESH_OT_select_path.bl_idname,dict(type='D',value=_A),dict(properties=[(_B,main.InteractEvent.CHANGE_DIRECTION.name)])),(main.MESH_OT_select_path.bl_idname,dict(type='C',value=_A),dict(properties=[(_B,main.InteractEvent.CLOSE_PATH.name)])),(main.MESH_OT_select_path.bl_idname,dict(type='Z',value=_A,shift=_C,ctrl=_C),dict(properties=[(_B,main.InteractEvent.REDO.name)])),(main.MESH_OT_select_path.bl_idname,dict(type='Z',value=_A,ctrl=_C),dict(properties=[(_B,main.InteractEvent.UNDO.name)])),(main.MESH_OT_select_path.bl_idname,dict(type='ESC',value=_A),dict(properties=[(_B,main.InteractEvent.CANCEL.name)])),(main.MESH_OT_select_path.bl_idname,dict(type='SPACE',value=_A),dict(properties=[(_B,main.InteractEvent.APPLY_PATHS.name)])),(main.MESH_OT_select_path.bl_idname,dict(type='RET',value=_A),dict(properties=[(_B,main.InteractEvent.APPLY_PATHS.name)])),(main.MESH_OT_select_path.bl_idname,dict(type='RIGHTMOUSE',value=_A),dict(properties=[(_B,main.InteractEvent.PIE.name)])),(main.MESH_OT_select_path.bl_idname,dict(type=_D,value=_A),dict(properties=[(_B,main.InteractEvent.NONE.name)])),(main.MESH_OT_select_path.bl_idname,dict(type=_D,value=_A),dict(properties=[(_B,main.InteractEvent.ADD_CP.name)]))
	@staticmethod
	def draw_settings(context:Context,layout:UILayout,tool:WorkSpaceTool):wm_props:WMProps=context.window_manager.select_path;layout.enabled=not wm_props.is_runtime;wm_props.ui_draw_func_runtime(layout)
@persistent
def load_post(_unused):bhqab.utils_ui.copy_default_presets_from(src_root=os.path.join(DATA_DIR,'presets'));bhqupd.check_addon_updates()
_classes=pref.Preferences,pref.PREFERENCES_MT_path_tool_appearance_preset,pref.PREFERENCES_OT_path_tool_appearance_preset,props.WMProps,props.MESH_MT_select_path_presets,props.MESH_OT_select_path_preset_add,props.PREFERENCES_OT_select_path_pref_show,main.MESH_OT_select_path,main.MESH_PT_select_path_context
_cls_register,_cls_unregister=bpy.utils.register_classes_factory(classes=_classes)
_handlers=(bpy.app.handlers.load_post,load_post),
def register():
	A=False;_cls_register();WindowManager.select_path=PointerProperty(type=props.WMProps);bpy.utils.register_tool(PathToolMesh,after={'builtin.select_lasso'},separator=A,group=A);bpy.app.translations.register(ADDON_PKG,langs.LANGS);bhqupd.register_addon_update_operators()
	for(handler,func)in _handlers:
		if func not in handler:handler.append(func)
def unregister():
	for(handler,func)in _handlers:
		if func not in handler:handler.remove(func)
	bpy.app.translations.unregister(ADDON_PKG);bhqupd.unregister_addon_update_operators();bpy.utils.unregister_tool(PathToolMesh);del WindowManager.select_path;_cls_unregister()