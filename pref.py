from __future__ import annotations
_N='preferences'
_M='path_tool'
_L='UPDATES'
_K='LICENSE'
_J='README'
_I='HIDDEN'
_H='APPEARANCE'
_G='LINKS'
_F='appearance'
_E=.0
_D='COLOR'
_C=1.
_B='SKIP_SAVE'
_A='Preferences'
import os
from.import ADDON_PKG
from.import INFO_DIR
from.import langs
from.import main
from.import icons
from.lib import bhqab
from.lib import bhqupd
from bpy.types import AddonPreferences,Context,KeyMap,Menu,Operator,OperatorProperties,UILayout
from bpy.props import BoolProperty,EnumProperty,FloatVectorProperty,IntProperty
from bl_operators.presets import AddPresetBase
from bpy.app.translations import pgettext
import rna_keymap_ui
from typing import TYPE_CHECKING
if TYPE_CHECKING:from.props import WMProps
PREF_TEXTS=dict()
class Preferences(AddonPreferences):
	bl_idname=ADDON_PKG;tab:EnumProperty(items=((_H,'Appearance','Appearance settings',icons.get_id(_F),1<<0),('BEHAVIOR','Behavior','Behavior settings',icons.get_id('behavior'),1<<1),('KEYMAP','Keymap','Keymap settings',icons.get_id('keymap'),1<<2),('INFO','Info','How to use the addon, relative links and licensing information',icons.get_id('info'),1<<3)),default=_H,options={_I,_B},translation_context=_A,name='Tab',description='User preferences tab to be displayed');info_tab:EnumProperty(items=((_J,'How To Use the Addon','',icons.get_id('readme'),1<<0),(_K,'License','',icons.get_id('license'),1<<1),(_L,'Updates','',icons.get_id('update'),1<<2),(_G,'Links','',icons.get_id('links'),1<<3)),default={_G},options={'ENUM_FLAG',_I,_B},translation_context=_A);color_control_element:FloatVectorProperty(default=(.8,.8,.8,.8),subtype=_D,size=4,min=_E,max=_C,options={_B},translation_context=_A,name='Control Element',description='Control element color');color_active_control_element:FloatVectorProperty(default=(.039087,.331906,.940392,.8),subtype=_D,size=4,min=_E,max=_C,options={_B},translation_context=_A,name='Active Control Element',description='Color of active control element');color_path:FloatVectorProperty(default=(.593397,.708376,.634955,.8),subtype=_D,size=4,min=_E,max=_C,options={_B},translation_context=_A,name='Path',description='Regular path color');color_path_topology:FloatVectorProperty(default=(_C,.952328,.652213,.8),subtype=_D,size=4,min=_E,max=_C,options={_B},translation_context=_A,name='Topology Path',description='Color of paths which uses topology calculation method');color_active_path:FloatVectorProperty(default=(.304987,.708376,.450786,.8),subtype=_D,size=4,min=_E,max=_C,options={_B},translation_context=_A,name='Active Path',description='Active path color');color_active_path_topology:FloatVectorProperty(default=(_C,.883791,.152213,.8),subtype=_D,size=4,min=_E,max=_C,options={_B},translation_context=_A,name='Active Topology Path',description='Color of active path which uses topology calculation method');color_path_behind:FloatVectorProperty(default=(.883791,.883791,.883791,.8),subtype=_D,size=4,min=_E,max=_C,options={_B},translation_context=_A,name='Path Behind Mesh',description='The color of the path displayed behind the mesh');point_size:IntProperty(default=3,min=0,max=50,soft_max=20,subtype='FACTOR',options={_B},translation_context=_A,name='Vertex Size',description='The size of the vertex that represents the control element');line_width:IntProperty(default=3,min=1,max=9,soft_min=3,soft_max=6,subtype='PIXEL',options={_B},translation_context=_A,name='Line Thickness',description='The thickness of the lines that mark the segments of the path');auto_tweak_options:BoolProperty(default=False,options={_B},translation_context=_A,name='Auto Tweak Options',description='Adjust operator options. If no mesh element is initially selected, the selection option will be changed to "Extend". If all elements are selected, it will be changed to "Do nothing"');aa_method:bhqab.utils_gpu.DrawFramework.get_prop_aa_method();fxaa_preset:bhqab.utils_gpu.FXAA.get_prop_preset();fxaa_value:bhqab.utils_gpu.FXAA.get_prop_value();smaa_preset:bhqab.utils_gpu.SMAA.get_prop_preset()
	def draw(self,context:Context)->None:
		E='QUESTION';D='Recommended';C='NONE';B='info_tab';A=True;layout:UILayout=self.layout;layout.use_property_split=A;row=layout.row();row.prop_tabs_enum(self,'tab')
		match self.tab:
			case'APPEARANCE':
				bhqab.utils_ui.template_preset(layout,menu=PREFERENCES_MT_path_tool_appearance_preset,operator=PREFERENCES_OT_path_tool_appearance_preset.bl_idname);col=layout.column(align=A);col.prop(self,'color_control_element');col.prop(self,'color_active_control_element');col.separator();col.prop(self,'color_path');col.prop(self,'color_active_path');col.separator();col.prop(self,'color_path_topology');col.prop(self,'color_active_path_topology');col.separator();col.prop(self,'color_path_behind');col.separator();col.prop(self,'point_size');col.prop(self,'line_width');col.separator();row=col.row(align=A);row.prop(self,'aa_method',expand=A)
				if self.aa_method=='FXAA':col.prop(self,'fxaa_preset');scol=col.column(align=A);scol.enabled=self.fxaa_preset not in{C,'ULTRA'};scol.prop(self,'fxaa_value')
				elif self.aa_method=='SMAA':col.prop(self,'smaa_preset')
				else:col.label(text='Unknown Anti-Aliasing Method.')
			case'BEHAVIOR':
				layout.prop(self,'auto_tweak_options');pref_inputs=context.preferences.inputs
				if not pref_inputs.use_mouse_depth_navigate:col=layout.column(align=A);col.label(text=D,icon=E);col.prop(context.preferences.inputs,'use_mouse_depth_navigate')
				if not pref_inputs.use_zoom_to_mouse:col=layout.column(align=A);col.label(text=D,icon=E);col.prop(context.preferences.inputs,'use_zoom_to_mouse')
			case'KEYMAP':
				wm=context.window_manager;wm_props:WMProps=wm.select_path;col=layout.column();col.enabled=not wm_props.is_runtime;kc=wm.keyconfigs.user;km:KeyMap=kc.keymaps.get(main.TOOL_KM_NAME)
				if km:
					for kmi in km.keymap_items:
						prop:set[str]=kmi.properties.action
						for item in main.ACTION_ITEMS:
							key,name,_desc,icon,_val=item
							if prop==key:row=col.row(align=A);srow=row.row();srow.ui_units_x=10;srow.alignment='RIGHT';srow.label(text=name,icon=icon,text_ctxt='MESH_OT_select_path');rna_keymap_ui.draw_kmi([],kc,km,kmi,row,0)
			case'INFO':
				for flag in(_J,_K):
					if bhqab.utils_ui.template_disclosure_enum_flag(layout,item=self,prop_enum_flag=B,flag=flag):text=bhqab.utils_ui.request_localization_from_file(module=ADDON_PKG,langs=langs.LANGS,msgctxt=flag,src=os.path.join(INFO_DIR,f"{flag}.txt"),dst={'uk':os.path.join(INFO_DIR,f"{flag}_uk.txt")});bhqab.utils_ui.draw_wrapped_text(context,layout,text=text,text_ctxt=flag)
				if bhqab.utils_ui.template_disclosure_enum_flag(layout,item=self,prop_enum_flag=B,flag=_L):bhqupd.ui_draw_updates_section(context,layout,cb_draw_wrapped_text=bhqab.utils_ui.draw_wrapped_text)
				if bhqab.utils_ui.template_disclosure_enum_flag(layout,item=self,prop_enum_flag=B,flag=_G):
					col_flow=layout.column_flow(columns=3,align=A)
					def _intern_draw_large_url(icon:str,text:str,url:str):col=col_flow.column(align=A);box=col.box();box.template_icon(icons.get_id(identifier=icon),scale=3.);scol=box.column();scol.emboss=C;scol.operator('wm.url_open',text=text,text_ctxt=_A).url=url
					_intern_draw_large_url(icon='patreon',text='Support Project on Patreon',url='https://www.patreon.com/BlenderHQ');_intern_draw_large_url(icon='github',text='Project on GitHub',url='https://github.com/BlenderHQ/path_tool');_intern_draw_large_url(icon='youtube',text='BlenderHQ on YouTube',url='https://www.youtube.com/@BlenderHQ')
class PREFERENCES_MT_path_tool_appearance_preset(Menu):bl_label='Appearance Preset';preset_subdir=os.path.join(_M,_N,_F);preset_operator='script.execute_preset';bl_translation_context='PREFERENCES_MT_path_tool_appearance_preset';draw=Menu.draw_preset
class PREFERENCES_OT_path_tool_appearance_preset(AddPresetBase,Operator):
	bl_idname='preferences.path_tool_appearance_preset';bl_label='';preset_menu=PREFERENCES_MT_path_tool_appearance_preset.__name__;preset_defines=[f'addon_pref = bpy.context.preferences.addons["{ADDON_PKG}"].preferences'];preset_values=['addon_pref.color_control_element','addon_pref.color_active_control_element','addon_pref.color_path','addon_pref.color_path_topology','addon_pref.color_active_path','addon_pref.color_active_path_topology','addon_pref.point_size','addon_pref.line_width'];preset_subdir=os.path.join(_M,_N,_F)
	@classmethod
	def description(cls,_context:Context,properties:OperatorProperties)->str:
		msgctxt=cls.__qualname__
		if properties.remove_active:return pgettext('Remove preset',msgctxt)
		else:return pgettext('Add preset',msgctxt)