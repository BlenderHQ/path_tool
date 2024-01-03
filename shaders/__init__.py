from __future__ import annotations
_J='f_Color'
_I='u_DepthMap'
_H='FLOAT_2D'
_G='u_Params'
_F='u_ViewportMetrics'
_E='ModelViewProjectionMatrix'
_D='MAT4'
_C='VEC3'
_B='common.vert'
_A='VEC4'
import os,gpu
from gpu.types import GPUShader,GPUShaderCreateInfo
from..lib import bhqglsl
from..lib.bhqglsl.ubo import glsl_bool,glsl_float,glsl_int,glsl_mat4,glsl_vec2,glsl_vec4
__all__='INTERN_DIR','CommonParams','get','register'
INTERN_DIR=os.path.join(os.path.dirname(__file__),'intern')
class CommonParams(bhqglsl.ubo.StructUBO):model_matrix:glsl_mat4;color_cp:glsl_vec4;color_active_cp:glsl_vec4;color_path:glsl_vec4;color_active_path:glsl_vec4;color_path_behind:glsl_vec4;index_active:glsl_int;point_size:glsl_float;show_path_behind:glsl_bool;_fields_=('model_matrix',glsl_mat4),('color_cp',glsl_vec4),('color_active_cp',glsl_vec4),('color_path',glsl_vec4),('color_active_path',glsl_vec4),('color_path_behind',glsl_vec4),('index_active',glsl_int),('point_size',glsl_float),('show_path_behind',glsl_bool),('_pad0',glsl_float)
def _create_shader_cp_vert()->GPUShader:vertexcode,fragcode,geocode=bhqglsl.read_shader_files(directory=INTERN_DIR,filenames=(_B,'cp_vert.frag','cp_vert.geom'));geocode=f"layout(points) in;\nlayout(triangle_strip, max_vertices = 12) out;\n{geocode}\n";defines=CommonParams.as_struct();return GPUShader(vertexcode=vertexcode,fragcode=fragcode,geocode=geocode,defines=defines)
def _create_shader_cp_face()->GPUShader:vertexcode,fragcode=bhqglsl.read_shader_files(directory=INTERN_DIR,filenames=(_B,'cp_face.frag'));info=GPUShaderCreateInfo();info.vertex_in(0,_C,'P');info.push_constant(_D,_E);info.push_constant(_A,_F);info.uniform_buf(0,CommonParams.__qualname__,_G);info.sampler(0,_H,_I);info.fragment_out(0,_A,_J);info.typedef_source(CommonParams.as_struct());info.vertex_source(vertexcode);info.fragment_source(fragcode);return gpu.shader.create_from_info(info)
def _create_shader_path_edge()->GPUShader:vertexcode,fragcode=bhqglsl.read_shader_files(directory=INTERN_DIR,filenames=(_B,'path_edge.frag'));info=GPUShaderCreateInfo();info.vertex_in(0,_C,'P');info.push_constant(_D,_E);info.push_constant(_A,_F);info.uniform_buf(0,CommonParams.__qualname__,_G);info.sampler(0,_H,_I);info.fragment_out(0,_A,_J);info.typedef_source(CommonParams.as_struct());info.vertex_source(vertexcode);info.fragment_source(fragcode);return gpu.shader.create_from_info(info)
def _create_shader_path_face()->GPUShader:vertexcode,fragcode=bhqglsl.read_shader_files(directory=INTERN_DIR,filenames=(_B,'path_face.frag'));info=GPUShaderCreateInfo();info.vertex_in(0,_C,'P');info.push_constant(_D,_E);info.push_constant(_A,_F);info.uniform_buf(0,CommonParams.__qualname__,_G);info.sampler(0,_H,_I);info.fragment_out(0,_A,_J);info.typedef_source(CommonParams.as_struct());info.vertex_source(vertexcode);info.fragment_source(fragcode);return gpu.shader.create_from_info(info)
_SHADERS=dict()
def get(name:str)->None|GPUShader:return _SHADERS.get(name,None)
def register():_SHADERS['cp_vert']=_create_shader_cp_vert();_SHADERS['cp_face']=_create_shader_cp_face();_SHADERS['path_edge']=_create_shader_path_edge();_SHADERS['path_face']=_create_shader_path_face()