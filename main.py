from __future__ import annotations
_V='PASS_THROUGH'
_U='cp_face'
_T='cp_vert'
_S='path_edge'
_R='SKIP_SAVE'
_Q='HIDDEN'
_P='MESH_OT_select_path'
_O='Select Path'
_N='3D View Tool: Edit Mesh, Select Path'
_M='EXTEND'
_L='CANCELLED'
_K='RUNNING_MODAL'
_J='INFO'
_I='VIEW_3D'
_H='DESELECT'
_G='edges'
_F='WINDOW'
_E='faces'
_D='NONE'
_C=True
_B=False
_A=None
from typing import Literal
import collections
from enum import auto,IntFlag
from.import ADDON_PKG
if'bpy'in locals():from importlib import reload;reload(bhqab);reload(bhqglsl);reload(shaders)
else:from.lib import bhqab,bhqglsl;from.import shaders
import bpy
from bpy.types import Area,Context,Event,KeyMap,KeyMapItem,Mesh,Object,Operator,Panel,Region,RegionView3D,SpaceView3D,UIPieMenu,Window
from bpy.props import EnumProperty
from bpy.app.translations import pgettext
import bmesh
from bmesh.types import BMEdge,BMesh,BMFace,BMVert
import gpu
from gpu.types import GPUBatch
from gpu_extras.batch import batch_for_shader
from typing import TYPE_CHECKING
if TYPE_CHECKING:from.props import WMProps;from.pref import Preferences
_REGION_VIEW_3D_N_PANEL_TABS_WIDTH_PX=21
TOOL_KM_NAME=_N
def eval_view3d_n_panel_width(context:Context)->int:return _REGION_VIEW_3D_N_PANEL_TABS_WIDTH_PX*context.preferences.view.ui_scale
class InteractEvent(IntFlag):NONE=auto();ADD_CP=auto();ADD_NEW_PATH=auto();REMOVE_CP=auto();DRAG_CP=auto();CLOSE_PATH=auto();CHANGE_DIRECTION=auto();TOPOLOGY_DISTANCE=auto();RELEASE_PATH=auto();UNDO=auto();REDO=auto();APPLY_PATHS=auto();CANCEL=auto();PIE=auto()
class PathFlag(IntFlag):CLOSED=auto();REVERSED=auto();TOPOLOGY=auto()
_PackedEvent_T=tuple[int|str,int|str,int|bool,int|bool,int|bool]
class Path:
	__slots__='island_index','ob','batch_control_elements','control_elements','fill_elements','batch_seq_fills','flag';island_index:int;ob:_A|Object;batch_control_elements:_A|GPUBatch;control_elements:list[BMVert|BMFace];fill_elements:list[list[BMEdge|BMFace]];batch_seq_fills:list[_A|GPUBatch];flag:PathFlag
	def __init__(self,elem:_A|BMVert|BMFace=_A,linked_island_index:int=0,ob:_A|Object=_A)->_A:
		self.island_index=linked_island_index;self.ob=ob;self.batch_control_elements=_A;self.control_elements=list();self.fill_elements=list();self.batch_seq_fills=list()
		if elem is not _A:self.control_elements.append(elem);self.fill_elements.append([]);self.batch_seq_fills.append(_A)
		self.flag=PathFlag(0)
	def __repr__(self):
		A='fb_%d';batch_seq_fills_formatted=[]
		for(i,batch)in enumerate(self.batch_seq_fills):
			if batch:batch_seq_fills_formatted.append(A%i);continue
			batch_seq_fills_formatted.append(batch)
		[A%i for i in range(len(self.batch_seq_fills))];return'\nPath [id:%d]:\n    ce: %s\n    fe: %s\n    fb: %s'%(id(self),str([n.index for n in self.control_elements]),str([len(n)for n in self.fill_elements]),str(batch_seq_fills_formatted))
	def copy(self)->Path:new_path=Path();new_path.control_elements=self.control_elements.copy();new_path.fill_elements=self.fill_elements.copy();new_path.batch_seq_fills=self.batch_seq_fills.copy();new_path.batch_control_elements=self.batch_control_elements;new_path.island_index=self.island_index;new_path.ob=self.ob;new_path.flag=self.flag;return new_path
	def reverse(self)->Path:self.control_elements.reverse();close_path_fill=self.fill_elements.pop(-1);close_path_batch=self.batch_seq_fills.pop(-1);self.fill_elements.reverse();self.batch_seq_fills.reverse();self.fill_elements.append(close_path_fill);self.batch_seq_fills.append(close_path_batch);self.flag^=PathFlag.REVERSED;return self
	def is_in_control_elements(self,elem:BMVert|BMFace)->_A|int:
		if elem in self.control_elements:return self.control_elements.index(elem)
	def is_in_fill_elements(self,elem:BMVert|BMFace)->_A|int:
		if isinstance(elem,BMVert):
			for(i,arr)in enumerate(self.fill_elements):
				arr:list[BMEdge]
				for edge in arr:
					edge:BMEdge
					for vert in edge.verts:
						vert:BMVert
						if elem==vert:return i
				del arr
		for(i,arr)in enumerate(self.fill_elements):
			arr:list[BMFace]
			if elem in arr:return i
	def insert_control_element(self,elem_index,elem):self.control_elements.insert(elem_index,elem);self.fill_elements.insert(elem_index,[]);self.batch_seq_fills.insert(elem_index,_A)
	def remove_control_element(self,elem)->_A:elem_index=self.control_elements.index(elem);self.pop_control_element(elem_index)
	def pop_control_element(self,elem_index:int)->BMVert|BMFace:
		elem=self.control_elements.pop(elem_index);pop_index=elem_index-1
		if elem_index==0:pop_index=0
		self.fill_elements.pop(pop_index);self.batch_seq_fills.pop(pop_index);return elem
	def get_pairs_items(self,elem_index):
		r_pairs=list();num_ce=len(self.control_elements)
		if num_ce<2:return r_pairs
		if elem_index>num_ce-1:elem_index=num_ce-1
		elem=self.control_elements[elem_index]
		if elem_index==0:r_pairs=[[elem,self.control_elements[1],0]]
		elif elem_index==len(self.control_elements)-1:r_pairs=[[elem,self.control_elements[elem_index-1],elem_index-1]]
		elif len(self.control_elements)>2:r_pairs=[[elem,self.control_elements[elem_index-1],elem_index-1],[elem,self.control_elements[elem_index+1],elem_index]]
		if self.flag&PathFlag.CLOSED and num_ce>2 and elem_index in(0,num_ce-1):r_pairs.extend([[self.control_elements[0],self.control_elements[-1],-1]])
		return r_pairs
CONTEXT_ACTION_ITEMS=(InteractEvent.CHANGE_DIRECTION.name,'Direction','Change the direction of the active path.\nThe active element of the path will be the final element from the opposite end of the path, from it will be formed a section to the next control element that you create.',_D,InteractEvent.CHANGE_DIRECTION.value),(InteractEvent.CLOSE_PATH.name,'Close Path','Connect the start and end of the active path',_D,InteractEvent.CLOSE_PATH.value),(InteractEvent.CANCEL.name,'Cancel','Cancel editing paths',_D,InteractEvent.CANCEL.value),(InteractEvent.APPLY_PATHS.name,'Apply','Apply changes to the grid according to the selected options',_D,InteractEvent.APPLY_PATHS.value),(InteractEvent.UNDO.name,'Undo','Take a step back',_D,InteractEvent.UNDO.value),(InteractEvent.REDO.name,'Redo','Redo previous undo',_D,InteractEvent.REDO.value),(InteractEvent.TOPOLOGY_DISTANCE.name,'Topology','Algorithm for determining the shortest path without taking into account the spatial distance, only the number of steps',_D,InteractEvent.TOPOLOGY_DISTANCE.value)
ACTION_ITEMS=CONTEXT_ACTION_ITEMS+((InteractEvent.NONE.name,_O,'',_D,InteractEvent.NONE.value),(InteractEvent.ADD_CP.name,'Add New Control Point','',_D,InteractEvent.ADD_CP.value),(InteractEvent.ADD_NEW_PATH.name,'Add New Path','',_D,InteractEvent.ADD_NEW_PATH.value),(InteractEvent.REMOVE_CP.name,'Remove Control Point','',_D,InteractEvent.REMOVE_CP.value),(InteractEvent.DRAG_CP.name,'Drag Control Point','',_D,InteractEvent.DRAG_CP.value),(InteractEvent.RELEASE_PATH.name,'Release Path','',_D,InteractEvent.RELEASE_PATH.value),(InteractEvent.PIE.name,'Open Pie Menu','',_D,InteractEvent.PIE.value))
class MESH_PT_select_path_context(Panel):
	bl_label='Options';bl_translation_context='MESH_PT_select_path_context';bl_space_type=_I;bl_region_type=_F
	def draw(cls,context:Context)->_A:layout=cls.layout;layout.ui_units_x=15;layout.use_property_split=_C;props:WMProps=context.window_manager.select_path;props.ui_draw_func_runtime(layout)
def __validate_context_action_items_display_symmetry_concept(bias:int=1):
	W,E,S,N,NE,NW,SW=(_[1]for _ in CONTEXT_ACTION_ITEMS);SE=MESH_PT_select_path_context.bl_label;len_cmp_order={'West <> East (important!)':(W,E),'North <> South (important!)':(N,S),'North-East <> South-East':(NE,SE),'North-West <> South-West':(NW,SW),'North-West <> North-East (important!)':(NW,NE),'South-West <> South-East (important!)':(SW,SE)}
	for(desc,pair)in len_cmp_order.items():
		l,r=pair
		if abs(len(l)-len(r))>bias:print(f'\'_context_action_items\' may look asymmetrical in direction: {desc}\n\t"{l}" {len(l)} characters\n\t"{r}" {len(r)} characters\n')
del __validate_context_action_items_display_symmetry_concept
class MESH_OT_select_path(Operator):
	bl_idname='mesh.select_path';bl_label=_O;bl_options={'REGISTER','UNDO','INTERNAL'};bl_translation_context=_P;__slots__=();context_action:EnumProperty(items=CONTEXT_ACTION_ITEMS,default=set(),options={'ENUM_FLAG',_Q,_R},translation_context=_P);action:EnumProperty(items=ACTION_ITEMS,default=InteractEvent.NONE.name,options={_Q,_R});windows:set[Window]=set();nav_events:tuple[_PackedEvent_T]=tuple();is_interaction:bool=_B;initial_ts_msm:tuple[int|bool,int|bool,int|bool];initial_mesh_elements:Literal[_G,_E];prior_ts_msm:tuple[int|bool,int|bool,int|bool];prior_mesh_elements:Literal[_G,_E];select_ts_msm:tuple[int|bool,int|bool,int|bool];select_mesh_elements:Literal['verts',_E];initial_select:tuple[BMVert|BMEdge|BMFace];bm_arr:tuple[tuple[Object,BMesh]];path_arr:list[Path]=list();mesh_islands:list[tuple[BMVert|BMEdge|BMFace]];drag_elem_indices:list[_A|int];_active_path_index:int=0;_drag_elem:_A|BMVert|BMFace=_A;_just_closed_path:bool=_B;gpu_draw_framework:_A|bhqab.utils_gpu.DrawFramework=_A;gpu_handles:list=list();gpu_common_ubo:_A|bhqglsl.ubo.UBO[shaders.CommonParams]=_A;undo_history:collections.deque[tuple[int,tuple[Path]]];redo_history:collections.deque[tuple[int,tuple[Path]]];exec_select_arr:dict[Object,list[tuple[int]]];exec_markup_arr:dict[Object,list[tuple[int]]]
	@staticmethod
	def _pack_event(item:KeyMapItem|Event)->_PackedEvent_T:return item.type,item.value,item.alt,item.ctrl,item.shift
	@classmethod
	def _eval_meshes(cls,context:Context)->_A:
		ret:list[tuple[Object,BMesh]]=list();props:WMProps=context.window_manager.select_path
		for ob in context.objects_in_mode:
			ob:Object;bm=bmesh.from_edit_mesh(ob.data)
			if cls.prior_ts_msm[1]:bm.edges.ensure_lookup_table()
			elif cls.prior_ts_msm[2]:
				bm.faces.ensure_lookup_table()
				if props.mark_seam!=_D or props.mark_sharp!=_D:bm.edges.ensure_lookup_table()
			ret.append((ob,bm))
		cls.bm_arr=tuple(ret)
	@classmethod
	def _invoke_tweak_options(cls,context:Context):
		wm=context.window_manager;props:WMProps=wm.select_path;addon_pref:Preferences=context.preferences.addons[ADDON_PKG].preferences
		if addon_pref.auto_tweak_options:
			num_elements_total=0
			if cls.prior_mesh_elements==_G:
				for(_,bm)in cls.bm_arr:num_elements_total+=len(bm.edges)
			elif cls.prior_mesh_elements==_E:
				for(_,bm)in cls.bm_arr:num_elements_total+=len(bm.faces)
			if num_elements_total==len(cls.initial_select)and props.mark_select==_M:props.mark_select=_D
			elif num_elements_total>len(cls.initial_select)and props.mark_select==_D:props.mark_select=_M
	@classmethod
	@property
	def active_path(cls)->Path:
		if len(cls.path_arr)-1>cls._active_path_index:return cls.path_arr[cls._active_path_index]
		return cls.path_arr[-1]
	@classmethod
	def set_active_path(cls,value:Path)->_A:cls._active_path_index=cls.path_arr.index(value)
	@staticmethod
	def _set_selection_state(elem_seq:tuple[BMVert|BMEdge|BMFace],state:bool=_C)->_A:
		for elem in elem_seq:elem.select=state
	@staticmethod
	def _get_interactive_ui_under_mouse(context:Context,event:Event)->_A|tuple[Area,Region,RegionView3D]:
		mx,my=event.mouse_x,event.mouse_y
		for area in bpy.context.window.screen.areas:
			area:Area
			if area.type==_I:
				for region in area.regions:
					if region.type==_F:
						if region.x<mx<region.x+region.width-eval_view3d_n_panel_width(context)and region.y<my<region.y+region.height:
							for space in area.spaces:
								if space.type==_I:
									space:SpaceView3D
									if space.region_quadviews:region_data=space.region_quadviews
									else:region_data=space.region_3d
							return area,region,region_data
	@classmethod
	def _get_element_by_mouse(cls,context:Context,event:Event)->tuple[_A|BMVert|BMEdge|BMFace,_A|Object]:
		ts=context.tool_settings;ts.mesh_select_mode=cls.select_ts_msm;bpy.ops.mesh.select_all(action=_H);ui=MESH_OT_select_path._get_interactive_ui_under_mouse(context,event)
		if ui is not _A:
			area,region,region_data=ui
			with context.temp_override(window=bpy.context.window,area=area,region=region,region_data=region_data):bpy.ops.view3d.select('EXEC_DEFAULT',location=(event.mouse_x-region.x,event.mouse_y-region.y))
		elem=_A;ob=_A
		for(ob,bm)in cls.bm_arr:
			elem=bm.select_history.active
			if elem:elem.select=_B;bm.select_history.clear();break
		ts.mesh_select_mode=cls.prior_ts_msm;return elem,ob
	@classmethod
	def _get_current_state_copy(cls)->tuple[int,tuple[Path]]:return tuple((cls._active_path_index,tuple(n.copy()for n in cls.path_arr)))
	def _undo(self,context:Context):
		cls=self.__class__
		if len(cls.undo_history)==1:cls.path_arr.clear()
		elif len(cls.undo_history)>1:step=cls.undo_history.pop();cls.redo_history.append(step);undo_step_active_path_index,undo_step_path_seq=cls.undo_history[-1];cls._active_path_index=undo_step_active_path_index;cls.path_arr=list(undo_step_path_seq);cls._just_closed_path=_B
	def _redo(self,context:Context)->_A:
		cls=self.__class__;msgctxt=cls.__qualname__
		if len(cls.redo_history)>0:step=cls.redo_history.pop();cls.undo_history.append(step);undo_step_active_path_index,undo_step_path_seq=cls.undo_history[-1];cls._active_path_index=undo_step_active_path_index;cls.path_arr=list(undo_step_path_seq);context.area.tag_redraw()
		else:self.report({'WARNING'},message=pgettext('Can not redo anymore',msgctxt))
	@classmethod
	def _register_undo_step(cls)->_A:step=cls._get_current_state_copy();cls.undo_history.append(step);cls.redo_history.clear()
	@classmethod
	def _get_linked_island_index(cls,context:Context,elem:BMVert|BMFace)->int:
		ts=context.tool_settings
		for(i,linked_island)in enumerate(cls.mesh_islands):
			if elem in linked_island:return i
		ts.mesh_select_mode=cls.select_ts_msm;bpy.ops.mesh.select_all(action=_H);elem.select_set(_C);num_initial_selected,num_selected=0,1
		while num_initial_selected!=num_selected:bpy.ops.mesh.select_linked(delimit={'NORMAL'});num_initial_selected=sum(ob.data.total_vert_sel for(ob,_)in cls.bm_arr);bpy.ops.mesh.select_more(use_face_step=_C);num_selected=sum(ob.data.total_vert_sel for(ob,_)in cls.bm_arr)
		linked_island=cls._get_selected_elements(cls.select_mesh_elements);ts.mesh_select_mode=cls.prior_ts_msm;bpy.ops.mesh.select_all(action=_H);cls.mesh_islands.append(linked_island);return len(cls.mesh_islands)-1
	@staticmethod
	def _update_mesh(*,bm:BMesh,mesh:Mesh)->_A:bm.select_flush_mode();bmesh.update_edit_mesh(mesh=mesh,loop_triangles=_B,destructive=_B)
	@classmethod
	def _update_meshes(cls)->_A:
		for(ob,bm)in cls.bm_arr:cls._update_mesh(bm=bm,mesh=ob.data)
	@classmethod
	def _update_fills_by_element_index(cls,context:Context,path:Path,elem_index:int)->_A:
		ts=context.tool_settings;pairs_items=path.get_pairs_items(elem_index)
		for(elem_0,elem_1,fill_index)in pairs_items:
			ts.mesh_select_mode=cls.select_ts_msm;bpy.ops.mesh.select_all(action=_H);cls._set_selection_state((elem_0,elem_1),_C);bpy.ops.mesh.shortest_path_select(use_topology_distance=bool(path.flag&PathFlag.TOPOLOGY));cls._set_selection_state((elem_0,elem_1),_B);fill_seq=cls._get_selected_elements(cls.prior_mesh_elements);bpy.ops.mesh.select_all(action=_H)
			if not fill_seq and isinstance(elem_0,BMVert):
				for edge in elem_0.link_edges:
					edge:BMEdge
					if edge.other_vert(elem_0)==elem_1:fill_seq=tuple((edge,))
			ts.mesh_select_mode=cls.prior_ts_msm;path.fill_elements[fill_index]=fill_seq;batch=_A;shader=shaders.get(_S)
			if cls.prior_ts_msm[1]:
				coord=[]
				for edge in fill_seq:coord.extend([vert.co for vert in edge.verts])
				batch=batch_for_shader(shader,'LINES',dict(P=coord))
			elif cls.prior_ts_msm[2]:batch,_=cls._gpu_gen_batch_faces_seq(fill_seq,_B,shader)
			path.batch_seq_fills[fill_index]=batch
	def _remove_path_doubles(self,context:Context,path:Path)->_A:
		cls=self.__class__;msgctxt=cls.__qualname__
		for(i,control_element)in enumerate(path.control_elements):
			if path.control_elements.count(control_element)>1:
				for(j,other_control_element)in enumerate(path.control_elements):
					if i!=j and other_control_element==control_element:
						if i==0 and j==len(path.control_elements)-1:
							path.pop_control_element(-1)
							if path.flag^PathFlag.CLOSED:
								path.flag|=PathFlag.CLOSED;cls._update_fills_by_element_index(context,path,0)
								if path==cls.active_path:cls._just_closed_path=_C;text=pgettext('Closed active path',msgctxt)
								else:text=pgettext('Closed path',msgctxt)
								self.report(type={_J},message=text)
							else:cls._update_fills_by_element_index(context,path,0)
						elif i in(j-1,j+1):path.pop_control_element(j);batch,_=cls._gpu_gen_batch_control_elements(path==cls.active_path,path);path.batch_control_elements=batch;self.report(type={_J},message=pgettext('Merged adjacent control elements',msgctxt))
	def _join_adjacent_to_active_path(self)->_A:
		cls=self.__class__;msgctxt=cls.__qualname__
		if cls.active_path.flag^PathFlag.CLOSED:
			l_path=cls.active_path
			for(i,r_path)in enumerate(cls.path_arr):
				if i!=cls._active_path_index and l_path.island_index==r_path.island_index and r_path.flag^PathFlag.CLOSED:
					is_joined=_C
					if l_path.control_elements[-1]==r_path.control_elements[0]:l_path.control_elements.pop(-1);l_path.fill_elements.pop(-1);l_path.batch_seq_fills.pop(-1);l_path.control_elements.extend(r_path.control_elements);l_path.fill_elements.extend(r_path.fill_elements);l_path.batch_seq_fills.extend(r_path.batch_seq_fills)
					elif l_path.control_elements[0]==r_path.control_elements[-1]:l_path.control_elements.pop(0);r_path.fill_elements.pop(-1);r_path.batch_seq_fills.pop(-1);r_path.control_elements.extend(l_path.control_elements);r_path.fill_elements.extend(l_path.fill_elements);r_path.batch_seq_fills.extend(l_path.batch_seq_fills);l_path.control_elements=r_path.control_elements;l_path.fill_elements=r_path.fill_elements;l_path.batch_seq_fills=r_path.batch_seq_fills
					elif l_path.control_elements[0]==r_path.control_elements[0]:l_path.control_elements.pop(0);r_path.control_elements.reverse();r_path.fill_elements.reverse();r_path.batch_seq_fills.reverse();r_path.fill_elements.pop(0);r_path.batch_seq_fills.pop(0);r_path.control_elements.extend(l_path.control_elements);r_path.fill_elements.extend(l_path.fill_elements);r_path.batch_seq_fills.extend(l_path.batch_seq_fills);l_path.control_elements=r_path.control_elements;l_path.fill_elements=r_path.fill_elements;l_path.batch_seq_fills=r_path.batch_seq_fills
					elif l_path.control_elements[-1]==r_path.control_elements[-1]:r_path.reverse();l_path.control_elements.pop(-1);l_path.fill_elements.pop(-1);l_path.batch_seq_fills.pop(-1);l_path.control_elements.extend(r_path.control_elements);l_path.fill_elements.extend(r_path.fill_elements);l_path.batch_seq_fills.extend(r_path.batch_seq_fills)
					else:is_joined=_B
					if is_joined:cls.path_arr.remove(r_path);cls._active_path_index=cls.path_arr.index(cls.active_path);batch,cls.active_index=cls._gpu_gen_batch_control_elements(_C,cls.active_path);cls.active_path.batch_control_elements=batch;self.report(type={_J},message=pgettext('Joined two paths',msgctxt));return
	@classmethod
	def _get_selected_elements(cls,mesh_elements:str)->tuple[BMVert|BMEdge|BMFace]:
		ret=tuple()
		for(_,bm)in cls.bm_arr:elem_arr=getattr(bm,mesh_elements);ret+=tuple(n for n in elem_arr if n.select)
		return ret
	def _ui_draw_popup_menu_pie(self,popup:UIPieMenu,context:Context)->_A:pie=popup.layout.menu_pie();pie.prop_tabs_enum(self,'context_action');pie.popover(MESH_PT_select_path_context.__name__)
	@staticmethod
	def _gpu_gen_batch_faces_seq(fill_seq,is_active,shader):
		tmp_bm=bmesh.new()
		for face in fill_seq:tmp_bm.faces.new((tmp_bm.verts.new(v.co,v)for v in face.verts),face)
		tmp_bm.verts.index_update();tmp_bm.faces.ensure_lookup_table();tmp_loops=tmp_bm.calc_loop_triangles();r_batch=batch_for_shader(shader,'TRIS',dict(P=tuple(v.co for v in tmp_bm.verts)),indices=tuple((loop.vert.index for loop in tri)for tri in tmp_loops));r_active_face_tri_start_index=_A
		if is_active:r_active_face_tri_start_index=len(tmp_loops);tmp_bm=bmesh.new();face=fill_seq[-1];tmp_bm.faces.new((tmp_bm.verts.new(v.co,v)for v in face.verts),face);r_active_face_tri_start_index-=len(tmp_bm.calc_loop_triangles())
		return r_batch,r_active_face_tri_start_index
	@classmethod
	def _gpu_gen_batch_control_elements(cls,is_active,path):
		shader=shaders.get(_T)
		if cls.prior_ts_msm[2]:shader=shaders.get(_U)
		r_batch=_A;r_active_elem_start_index=0
		if cls.prior_ts_msm[1]:
			r_batch=batch_for_shader(shader,'POINTS',dict(P=tuple(v.co for v in path.control_elements)))
			if is_active:r_active_elem_start_index=len(path.control_elements)-1
		elif cls.prior_ts_msm[2]:r_batch,r_active_elem_start_index=cls._gpu_gen_batch_faces_seq(path.control_elements,is_active,shader)
		return r_batch,r_active_elem_start_index
	@classmethod
	def _gpu_remove_handles(cls)->_A:
		for handle in cls.gpu_handles:SpaceView3D.draw_handler_remove(handle,_F)
		cls.gpu_handles.clear();cls.gpu_common_ubo=_A
	@classmethod
	def _gpu_update_common_ubo(cls,context:Context):
		if not cls.gpu_common_ubo:cls.gpu_common_ubo=bhqglsl.ubo.UBO(ubo_type=shaders.CommonParams)
	@classmethod
	def _gpu_draw_callback(cls:MESH_OT_select_path)->_A:
		D='u_ViewportMetrics';C='u_DepthMap';B='u_Params';A=.0;context=bpy.context;addon_pref:Preferences=context.preferences.addons[ADDON_PKG].preferences;wm=context.window_manager;wm_props:WMProps=wm.select_path;draw_list:list[Path]=[_ for _ in cls.path_arr if _!=cls.active_path];draw_list.append(cls.active_path);shader_ce=shaders.get(_T);shader_path=shaders.get(_S)
		if cls.prior_ts_msm[2]:shader_ce=shaders.get(_U);shader_path=shaders.get('path_face')
		depth_map=bhqab.utils_gpu.get_depth_map();fb_framework=cls.gpu_draw_framework.get(index=0);fb=fb_framework.get()
		with fb.bind():
			fb.clear(color=(A,A,A,A));viewport_metrics=bhqab.utils_gpu.get_viewport_metrics()
			with gpu.matrix.push_pop():
				gpu.state.line_width_set(addon_pref.line_width);gpu.state.blend_set('ALPHA');gpu.state.face_culling_set(_D)
				for path in draw_list:
					active_ce_index=0;color_ce=addon_pref.color_control_element;color_active_ce=color_ce;color_path=addon_pref.color_path
					if path.flag&PathFlag.TOPOLOGY:color_path=addon_pref.color_path_topology
					if path==cls.active_path:
						active_ce_index=cls.active_index;color_active_ce=addon_pref.color_active_control_element;color_path=addon_pref.color_active_path
						if path.flag&PathFlag.TOPOLOGY:color_path=addon_pref.color_active_path_topology
					params=cls.gpu_common_ubo.data;params.model_matrix=tuple(_[:]for _ in path.ob.matrix_world.col);params.color_path=color_path[:];params.color_cp=color_ce[:];params.color_active_cp=color_active_ce[:];params.color_path_behind=addon_pref.color_path_behind[:];params.show_path_behind=wm_props.show_path_behind;params.index_active=active_ce_index
					if cls.prior_ts_msm[1]:params.point_size=addon_pref.point_size+6.
					cls.gpu_common_ubo.update();shader_path.bind()
					for batch in path.batch_seq_fills:
						if batch:shader_path.uniform_block(B,cls.gpu_common_ubo.ubo);shader_path.uniform_sampler(C,depth_map);shader_path.uniform_float(D,viewport_metrics);batch.draw(shader_path)
					shader_ce.bind()
					if path.batch_control_elements:shader_ce.uniform_block(B,cls.gpu_common_ubo.ubo);shader_ce.uniform_sampler(C,depth_map);shader_ce.uniform_float(D,viewport_metrics);path.batch_control_elements.draw(shader_ce)
		cls.gpu_draw_framework.draw(texture=fb_framework.get_color_texture())
	def _interact_control_element(self,context:Context,elem:_A|BMVert|BMFace,ob:Object,interact_event:InteractEvent)->_A:
		cls=self.__class__;msgctxt=cls.__qualname__;props:WMProps=context.window_manager.select_path
		if interact_event is InteractEvent.UNDO:self._undo(context)
		elif interact_event is InteractEvent.REDO:self._redo(context)
		elif elem and interact_event is InteractEvent.ADD_CP:
			if not cls.path_arr:return self._interact_control_element(context,elem,ob,InteractEvent.ADD_NEW_PATH)
			new_elem_index=_A;elem_index=cls.active_path.is_in_control_elements(elem)
			if elem_index is _A:
				new_elem_index=len(cls.active_path.control_elements);fill_index=cls.active_path.is_in_fill_elements(elem)
				if fill_index is _A:
					is_found_in_other_path=_B
					for path in cls.path_arr:
						if path==cls.active_path:continue
						other_elem_index=path.is_in_control_elements(elem)
						if other_elem_index is _A:
							other_fill_index=path.is_in_fill_elements(elem)
							if other_fill_index is not _A:is_found_in_other_path=_C
						else:is_found_in_other_path=_C
						if is_found_in_other_path:cls.set_active_path(path);cls._just_closed_path=_B;self._interact_control_element(context,elem,ob,InteractEvent.ADD_CP);return
				else:new_elem_index=fill_index+1;cls._just_closed_path=_B
			elif len(cls.active_path.control_elements)==1:batch,cls.active_index=cls._gpu_gen_batch_control_elements(_C,cls.active_path);cls.active_path.batch_control_elements=batch
			if elem_index is not _A:cls.drag_elem_indices=[path.is_in_control_elements(elem)for path in cls.path_arr];cls._just_closed_path=_B
			cls._drag_elem=elem
			if cls._just_closed_path:return self._interact_control_element(context,elem,ob,InteractEvent.ADD_NEW_PATH)
			if new_elem_index is not _A:
				linked_island_index=cls._get_linked_island_index(context,elem)
				if cls.active_path.island_index!=linked_island_index:return self._interact_control_element(context,elem,ob,InteractEvent.ADD_NEW_PATH)
				cls.active_path.insert_control_element(new_elem_index,elem);cls._update_fills_by_element_index(context,cls.active_path,new_elem_index);batch,cls.active_index=cls._gpu_gen_batch_control_elements(_C,cls.active_path);cls.active_path.batch_control_elements=batch;cls.drag_elem_indices=[path.is_in_control_elements(elem)for path in cls.path_arr]
		elif elem and interact_event is InteractEvent.ADD_NEW_PATH:
			linked_island_index=cls._get_linked_island_index(context,elem);new_path=Path(elem,linked_island_index,ob)
			if props.use_topology_distance:new_path.flag|=PathFlag.TOPOLOGY
			cls.path_arr.append(new_path);cls.set_active_path(new_path);cls._just_closed_path=_B;self._interact_control_element(context,elem,ob,InteractEvent.ADD_CP);self.report(type={_J},message=pgettext('Created new path',msgctxt))
		elif elem and interact_event is InteractEvent.REMOVE_CP:
			cls._just_closed_path=_B;elem_index=cls.active_path.is_in_control_elements(elem)
			if elem_index is _A:
				for path in cls.path_arr:
					other_elem_index=path.is_in_control_elements(elem)
					if other_elem_index is not _A:cls.set_active_path(path);self._interact_control_element(context,elem,ob,InteractEvent.REMOVE_CP);return
			else:
				cls.active_path.pop_control_element(elem_index)
				if not len(cls.active_path.control_elements):
					cls.path_arr.remove(cls.active_path)
					if len(cls.path_arr):cls.set_active_path(cls.path_arr[-1])
				else:cls._update_fills_by_element_index(context,cls.active_path,elem_index);batch,cls.active_index=cls._gpu_gen_batch_control_elements(_C,cls.active_path);cls.active_path.batch_control_elements=batch
		elif elem and interact_event is InteractEvent.DRAG_CP:
			if not cls._drag_elem or len(cls.drag_elem_indices)!=len(cls.path_arr):return
			cls._just_closed_path=_B;linked_island_index=cls._get_linked_island_index(context,elem)
			if cls.active_path.island_index==linked_island_index:
				cls._drag_elem=elem
				for(i,path)in enumerate(cls.path_arr):
					j=cls.drag_elem_indices[i]
					if j is not _A:path.control_elements[j]=elem;cls._update_fills_by_element_index(context,path,j);path.batch_control_elements,cls.active_index=cls._gpu_gen_batch_control_elements(path==cls.active_path,path)
		elif interact_event is InteractEvent.CHANGE_DIRECTION:cls.active_path.reverse();batch,cls.active_index=cls._gpu_gen_batch_control_elements(_C,cls.active_path);cls.active_path.batch_control_elements=batch;cls._just_closed_path=_B
		elif interact_event is InteractEvent.CLOSE_PATH:
			cls.active_path.flag^=PathFlag.CLOSED
			if cls.active_path.flag&PathFlag.CLOSED:
				cls._update_fills_by_element_index(context,cls.active_path,0)
				if len(cls.active_path.control_elements)>2:cls._just_closed_path=_C
			else:cls.active_path.fill_elements[-1]=[];cls.active_path.batch_seq_fills[-1]=_A;cls._just_closed_path=_B;self._join_adjacent_to_active_path()
		elif interact_event is InteractEvent.TOPOLOGY_DISTANCE:
			cls.active_path.flag^=PathFlag.TOPOLOGY
			for j in range(0,len(cls.active_path.control_elements),2):cls._update_fills_by_element_index(context,cls.active_path,j)
		elif interact_event is InteractEvent.RELEASE_PATH:
			cls.drag_elem_indices.clear();cls._drag_elem=_A
			for path in cls.path_arr:self._remove_path_doubles(context,path)
			self._join_adjacent_to_active_path();cls._register_undo_step()
	def draw(self,context:Context)->_A:layout=self.layout;layout.use_property_split=_C;props:WMProps=context.window_manager.select_path;props.ui_draw_func(layout)
	def invoke(self,context:Context,event):
		cls=self.__class__
		if self.context_action or InteractEvent.NONE.name!=self.action:return{_V}
		wm=context.window_manager
		if not cls.windows:
			cls.windows.add(context.window)
			for window in wm.windows:
				window:Window
				if context.window!=window:
					for area in window.screen.areas:
						area:Area
						if area.type==_I:
							for region in area.regions:
								region:Region
								if region.type==_F:break
							else:continue
							break
					else:continue
					with context.temp_override(window=window,area=area,region=region):bpy.ops.mesh.select_path('INVOKE_DEFAULT');cls.windows.add(window)
		else:wm.modal_handler_add(self);return{_K}
		ts=context.scene.tool_settings;num_undo_steps=context.preferences.edit.undo_steps;kc=wm.keyconfigs.user;km_path_tool=kc.keymaps[_N];kmi=km_path_tool.keymap_items[0];nav_events=[]
		for kmi in kc.keymaps['3D View'].keymap_items:
			kmi:KeyMapItem
			if kmi.idname in('view3d.rotate','view3d.move','view3d.zoom','view3d.dolly','view3d.view_center_camera','view3d.view_center_lock','view3d.view_all','view3d.navigate','view3d.view_camera','view3d.view_axis','view3d.view_orbit','view3d.view_persportho','view3d.view_pan','view3d.view_roll','view3d.view_center_pick','view3d.view_selected'):
				ev=list(cls._pack_event(kmi))
				if ev[0]=='WHEELINMOUSE':ev[0]='WHEELUPMOUSE'
				elif ev[0]=='WHEELOUTMOUSE':ev[0]='WHEELDOWNMOUSE'
				nav_events.append(tuple(ev))
		cls.nav_events=tuple(nav_events);cls.path_arr.clear();cls.mesh_islands=list();cls.drag_elem_indices=list();cls._active_path_index=0;cls._drag_elem=_A;cls._just_closed_path=_B;cls.gpu_handles=list();cls.undo_history=collections.deque(maxlen=num_undo_steps);cls.redo_history=collections.deque(maxlen=num_undo_steps);cls.exec_select_arr=dict();cls.exec_markup_arr=dict();cls.initial_ts_msm=tuple(ts.mesh_select_mode);cls.initial_mesh_elements=_G
		if cls.initial_ts_msm[2]:cls.initial_mesh_elements=_E
		cls.prior_ts_msm=_B,_C,_B;cls.prior_mesh_elements=_G;cls.select_ts_msm=_C,_B,_B;cls.select_mesh_elements='verts'
		if cls.initial_ts_msm[2]:cls.prior_ts_msm=_B,_B,_C;cls.prior_mesh_elements=_E;cls.select_ts_msm=_B,_B,_C;cls.select_mesh_elements=_E
		cls._eval_meshes(context);cls.initial_select=cls._get_selected_elements(cls.initial_mesh_elements);cls._invoke_tweak_options(context);elem,ob=cls._get_element_by_mouse(context,event)
		if not elem:cls._cancel_all_instances(context);return{_L}
		cls.gpu_handles=[SpaceView3D.draw_handler_add(self._gpu_draw_callback,tuple(),_F,'POST_VIEW')];shaders.register();cls._gpu_update_common_ubo(context);cls.gpu_draw_framework=bhqab.utils_gpu.DrawFramework(num=1);self._interact_control_element(context,elem,ob,InteractEvent.ADD_NEW_PATH);wm.modal_handler_add(self);return self.modal(context,event)
	@classmethod
	def _cancel_all_instances(cls,context:Context)->_A:wm_props:WMProps=context.window_manager.select_path;cls.windows.clear();ts=context.tool_settings;ts.mesh_select_mode=cls.initial_ts_msm;cls._set_selection_state(cls.initial_select,_C);cls._update_meshes();cls._gpu_remove_handles();wm_props.is_runtime=_B
	def cancel(self,context:Context):
		cls=self.__class__
		if context.window in cls.windows:cls.windows.remove(context.window)
		if not cls.windows:cls._cancel_all_instances(context)
	def modal(self,context:Context,event:Event):
		cls=self.__class__
		if not cls.windows:return{_L}
		wm=context.window_manager;wm_props:WMProps=wm.select_path;addon_pref:Preferences=context.preferences.addons[ADDON_PKG].preferences;ev=cls._pack_event(event);interact_event=_A;kc=context.window_manager.keyconfigs.user;km:KeyMap=kc.keymaps.get(TOOL_KM_NAME);kmi:_A|KeyMapItem=km.keymap_items.match_event(event)
		if InteractEvent.CANCEL.name in self.context_action or kmi and InteractEvent.CANCEL.name==kmi.properties.action:cls._cancel_all_instances(context);return{_L}
		elif InteractEvent.APPLY_PATHS.name in self.context_action or kmi and InteractEvent.APPLY_PATHS.name==kmi.properties.action:cls.windows.clear();cls._eval_final_element_indices_arrays();cls._gpu_remove_handles();return self.execute(context)
		elif cls._get_interactive_ui_under_mouse(context,event)is _A:return{_K}
		elif ev in cls.nav_events:return{_V}
		elif InteractEvent.CLOSE_PATH.name in self.context_action or kmi and InteractEvent.CLOSE_PATH.name==kmi.properties.action:interact_event=InteractEvent.CLOSE_PATH
		elif InteractEvent.CHANGE_DIRECTION.name in self.context_action or kmi and InteractEvent.CHANGE_DIRECTION.name==kmi.properties.action:interact_event=InteractEvent.CHANGE_DIRECTION
		elif InteractEvent.TOPOLOGY_DISTANCE.name in self.context_action or kmi and InteractEvent.TOPOLOGY_DISTANCE.name==kmi.properties.action:interact_event=InteractEvent.TOPOLOGY_DISTANCE
		elif InteractEvent.UNDO.name in self.context_action or kmi and InteractEvent.UNDO.name==kmi.properties.action:interact_event=InteractEvent.UNDO
		elif InteractEvent.REDO.name in self.context_action or kmi and InteractEvent.REDO.name==kmi.properties.action:interact_event=InteractEvent.REDO
		elif kmi and InteractEvent.ADD_CP.name==kmi.properties.action:cls.is_interaction=_C;interact_event=InteractEvent.ADD_CP
		elif kmi and InteractEvent.ADD_NEW_PATH.name==kmi.properties.action:cls.is_interaction=_C;interact_event=InteractEvent.ADD_NEW_PATH
		elif kmi and InteractEvent.REMOVE_CP.name==kmi.properties.action:interact_event=InteractEvent.REMOVE_CP
		if cls.is_interaction:
			if'MOUSEMOVE'==event.type:interact_event=InteractEvent.DRAG_CP
			elif'RELEASE'==event.value:cls.is_interaction=_B;interact_event=InteractEvent.RELEASE_PATH
		if kmi and InteractEvent.PIE.name==kmi.properties.action:cls.is_interaction=_B;context.window_manager.popup_menu_pie(event=event,draw_func=self._ui_draw_popup_menu_pie,title='Path Tool',icon=_D);return{_K}
		elif interact_event is not _A:elem,ob=cls._get_element_by_mouse(context,event);self._interact_control_element(context,elem,ob,interact_event);cls._set_selection_state(cls.initial_select,_C);cls._update_meshes()
		if not len(cls.path_arr):cls._cancel_all_instances(context);return{_L}
		self.context_action=set();cls.gpu_draw_framework.aa_method=addon_pref.aa_method
		if addon_pref.aa_method=='FXAA':cls.gpu_draw_framework.aa.preset=addon_pref.fxaa_preset;cls.gpu_draw_framework.aa.value=addon_pref.fxaa_value
		elif addon_pref.aa_method=='SMAA':cls.gpu_draw_framework.aa.preset=addon_pref.smaa_preset
		cls.gpu_draw_framework.modal_eval(context,color_format='RGBA32F',depth_format='DEPTH_COMPONENT32F',percentage=100);wm_props.is_runtime=_C;return{_K}
	@classmethod
	def _eval_final_element_indices_arrays(cls)->_A:
		cls.exec_select_arr=dict();cls.exec_markup_arr=dict()
		for(ob,_bm)in cls.bm_arr:
			index_select_seq=[];index_markup_seq=[]
			for path in cls.path_arr:
				if path.ob==ob:
					for fill_seq in path.fill_elements:index_select_seq.extend([_.index for _ in fill_seq])
					if cls.prior_ts_msm[1]:index_markup_seq=index_select_seq
					if cls.prior_ts_msm[2]:
						index_select_seq.extend([face.index for face in path.control_elements]);tmp=path.fill_elements;tmp.append(path.control_elements)
						for fill_seq in tmp:
							for face in fill_seq:index_markup_seq.extend([e.index for e in face.edges])
				cls.exec_select_arr[ob]=list(dict.fromkeys(index_select_seq));cls.exec_markup_arr[ob]=list(dict.fromkeys(index_markup_seq))
		cls._update_meshes()
	def execute(self,context:Context):
		C='TOGGLE';B='CLEAR';A='MARK';cls=self.__class__;ts=context.tool_settings;wm_props=context.window_manager.select_path;ts.mesh_select_mode=cls.prior_ts_msm;cls._eval_meshes(context);cls.initial_select=cls._get_selected_elements(cls.prior_mesh_elements)
		for(ob,bm)in cls.bm_arr:
			if wm_props.mark_select!=_D:
				index_select_seq=cls.exec_select_arr[ob];elem_seq=bm.edges
				if cls.prior_ts_msm[2]:elem_seq=bm.faces
				if wm_props.mark_select==_M:
					for i in index_select_seq:elem_seq[i].select_set(_C)
				elif wm_props.mark_select=='SUBTRACT':
					for i in index_select_seq:elem_seq[i].select_set(_B)
				elif wm_props.mark_select=='INVERT':
					for i in index_select_seq:elem_seq[i].select_set(not elem_seq[i].select)
			index_markup_seq=cls.exec_markup_arr[ob];elem_seq=bm.edges
			if wm_props.mark_seam!=_D:
				if wm_props.mark_seam==A:
					for i in index_markup_seq:elem_seq[i].seam=_C
				elif wm_props.mark_seam==B:
					for i in index_markup_seq:elem_seq[i].seam=_B
				elif wm_props.mark_seam==C:
					for i in index_markup_seq:elem_seq[i].seam=not elem_seq[i].seam
			if wm_props.mark_sharp!=_D:
				if wm_props.mark_sharp==A:
					for i in index_markup_seq:elem_seq[i].smooth=_B
				elif wm_props.mark_sharp==B:
					for i in index_markup_seq:elem_seq[i].smooth=_C
				elif wm_props.mark_sharp==C:
					for i in index_markup_seq:elem_seq[i].smooth=not elem_seq[i].smooth
		wm_props.is_runtime=_B;self._update_meshes();return{'FINISHED'}