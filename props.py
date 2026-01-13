from __future__ import annotations
_Q='props.mark_seam'
_P='path_tool'
_O='ACTION_TWEAK'
_N='Toggle'
_M='TOGGLE'
_L='RESTRICT_SELECT_ON'
_K='RESTRICT_SELECT_OFF'
_J='Select'
_I='EXTEND'
_H='HIDDEN'
_G='UPDATES'
_F=False
_E=True
_D='SKIP_SAVE'
_C='Do nothing'
_B='NONE'
_A='WMProps'
import os
from.import ADDON_PKG
from.import icons
from.lib import bhqab
from.lib import bhqupd
import bpy
from bpy.types import Context,Menu,Operator,OperatorProperties,PropertyGroup,UILayout
from bpy.props import BoolProperty,EnumProperty
from bl_operators.presets import AddPresetBase
from bpy.app.translations import pgettext
from typing import TYPE_CHECKING
if TYPE_CHECKING:from.pref import Preferences
def _get_addon_preferences(context:Context):
	'''Safely get addon preferences, handling versioned folder names.'''
	addons=context.preferences.addons
	if ADDON_PKG in addons:return addons[ADDON_PKG].preferences
	for name in addons.keys():
		if name.startswith('path_tool'):return addons[name].preferences
	return None
class WMProps(PropertyGroup):
	is_runtime:BoolProperty(options={_H});mark_select:EnumProperty(items=((_I,'Extend','Extend existing selection','SELECT_EXTEND',1),(_B,_C,_C,'X',2),('SUBTRACT','Subtract','Subtract existing selection','SELECT_SUBTRACT',3),('INVERT','Invert','Inverts existing selection','SELECT_DIFFERENCE',4)),default=_I,options={_D},translation_context=_A,name=_J,description='Selection options');mark_seam:EnumProperty(items=(('MARK','Mark','Mark seam path elements',_K,1),(_B,_C,_C,'X',2),('CLEAR','Clear','Clear seam path elements',_L,3),(_M,_N,'Toggle seams on path elements',_O,4)),default=_B,options={_D},translation_context=_A,name='Seam',description='Mark seam options');mark_sharp:EnumProperty(items=(('MARK','Mark','Mark sharp path elements',_K,1),(_B,_C,_C,'X',2),('CLEAR','Clear','Clear sharp path elements',_L,3),(_M,_N,'Toggle sharpness on path',_O,4)),default=_B,options={_D},translation_context=_A,name='Sharp',description='Mark sharp options');use_topology_distance:BoolProperty(default=_F,options={_D},translation_context=_A,name='Use Topology Distance',description='Use the algorithm for determining the shortest path without taking into account the spatial distance, only the number of steps. Newly created paths will use the value of the option, but this can be adjusted individually for each of them');show_path_behind:BoolProperty(default=_E,options={_D},translation_context=_A,name='Show Path Behind',description='Whether to show the path behind the mesh')
	def ui_draw_func(self,layout:UILayout)->None:
		bhqab.utils_ui.template_preset(layout,menu=MESH_MT_select_path_presets,operator=MESH_OT_select_path_preset_add.bl_idname);lay=layout
		if bpy.context.region.type in{'WINDOW','UI'}:lay=layout.column()
		def _intern_draw_enum_prop(identifier:str,text:str):row=lay.row();row.prop(self,identifier,text=text,icon_only=_E,expand=_E,text_ctxt=_A,translate=_E)
		_intern_draw_enum_prop('mark_select',_J);_intern_draw_enum_prop('mark_seam','Seam');_intern_draw_enum_prop('mark_sharp','Sharp')
	def ui_draw_func_runtime(self,layout:UILayout)->None:
		row=layout.row(align=_E)
		if bhqupd.has_updates():props=row.operator(operator=PREFERENCES_OT_select_path_pref_show.bl_idname,text='Update Available',text_ctxt=_A,emboss=_F);props.shortcut=_G
		else:row.operator(operator=PREFERENCES_OT_select_path_pref_show.bl_idname,text='Tool Settings',text_ctxt=_A,icon_value=icons.get_id('preferences'),emboss=_F)
		self.ui_draw_func(layout);layout.prop(self,'use_topology_distance');layout.prop(self,'show_path_behind')
class MESH_MT_select_path_presets(Menu):bl_label='Operator Preset';preset_subdir=os.path.join(_P,'wm');preset_operator='script.execute_preset';draw=Menu.draw_preset
class MESH_OT_select_path_preset_add(AddPresetBase,Operator):
	bl_idname='mesh.select_path_preset_add';bl_label='';bl_translation_context='MESH_OT_select_path_preset_add';preset_menu=MESH_MT_select_path_presets.__name__;preset_defines=['props = bpy.context.window_manager.select_path'];preset_values=['props.mark_select',_Q,_Q,'props.use_topology_distance'];preset_subdir=os.path.join(_P,'wm')
	@classmethod
	def description(cls,_context:Context,properties:OperatorProperties)->str:
		msgctxt=cls.__qualname__
		if properties.remove_active:return pgettext('Remove preset',msgctxt)
		else:return pgettext('Add preset',msgctxt)
class PREFERENCES_OT_select_path_pref_show(Operator):
	bl_idname='mesh.select_path_pref_show';bl_label='Show Preferences';bl_description='Path Tool user preferences';bl_translation_context='CPP_OT_pref_show';bl_options={'REGISTER'};shortcut:EnumProperty(items=((_B,'',''),(_G,'','')),default=_B,options={_H,_D})
	def execute(self,context:Context):
		addon_pref=_get_addon_preferences(context)
		if addon_pref is not None:
			match self.shortcut:
				case'UPDATES':addon_pref.tab='INFO';addon_pref.info_tab={_G}
		return bpy.ops.preferences.addon_show('EXEC_DEFAULT',module=ADDON_PKG)