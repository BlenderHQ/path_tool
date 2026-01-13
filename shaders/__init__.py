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
import os
import gpu
from gpu.types import GPUShader,GPUShaderCreateInfo,GPUStageInterfaceInfo
from..lib import bhqglsl
from..lib.bhqglsl.ubo import glsl_bool,glsl_float,glsl_int,glsl_mat4,glsl_vec2,glsl_vec4
__all__='INTERN_DIR','CommonParams','get','register'
INTERN_DIR=os.path.join(os.path.dirname(__file__),'intern')

class CommonParams(bhqglsl.ubo.StructUBO):
	model_matrix:glsl_mat4
	color_cp:glsl_vec4
	color_active_cp:glsl_vec4
	color_path:glsl_vec4
	color_active_path:glsl_vec4
	color_path_behind:glsl_vec4
	index_active:glsl_int
	point_size:glsl_float
	show_path_behind:glsl_bool
	_fields_=(
		('model_matrix',glsl_mat4),
		('color_cp',glsl_vec4),
		('color_active_cp',glsl_vec4),
		('color_path',glsl_vec4),
		('color_active_path',glsl_vec4),
		('color_path_behind',glsl_vec4),
		('index_active',glsl_int),
		('point_size',glsl_float),
		('show_path_behind',glsl_bool),
		('_pad0',glsl_float)
	)

def _create_shader_cp_vert()->GPUShader:
	'''Control point shader for vertex mode - uses point sprites instead of geometry shader.'''
	info=GPUShaderCreateInfo()
	# Vertex inputs
	info.vertex_in(0,_C,'P')
	info.vertex_in(1,'INT','v_Index')
	# Push constants
	info.push_constant(_D,_E)
	info.push_constant(_A,_F)
	# Uniform buffer
	info.uniform_buf(0,CommonParams.__qualname__,_G)
	# Sampler
	info.sampler(0,_H,_I)
	# Stage interface for passing data to fragment
	vert_out=GPUStageInterfaceInfo("cp_vert_iface")
	vert_out.flat('INT',"f_IsActive")
	info.vertex_out(vert_out)
	# Fragment output
	info.fragment_out(0,_A,_J)
	# Typedef for UBO struct
	info.typedef_source(CommonParams.as_struct())
	# Vertex shader
	info.vertex_source('''
void main() {
	gl_Position = ModelViewProjectionMatrix * u_Params.model_matrix * vec4(P, 1.0);
	gl_PointSize = u_Params.point_size * 2.0;
	f_IsActive = (v_Index >= u_Params.index_active) ? 1 : 0;
}
''')
	# Fragment shader - draw circular point
	info.fragment_source('''
#define BHQGLSL_PI 3.141592653589793
#define BHQGLSL_EXP 1e-5
bool frag_depth_greater_biased(in sampler2D depth_map, in vec2 view_resolution) {
	return (gl_FragCoord.z > texture(depth_map, vec2(gl_FragCoord.xy / view_resolution)).r + 1e-6);
}
void main() {
	// Discard fragments outside circle
	vec2 coord = gl_PointCoord * 2.0 - 1.0;
	float dist = dot(coord, coord);
	if (dist > 1.0) discard;
	// Depth test
	if (frag_depth_greater_biased(u_DepthMap, u_ViewportMetrics.zw)) {
		discard;
	}
	f_Color = (f_IsActive == 0) ? u_Params.color_cp : u_Params.color_active_cp;
}
''')
	return gpu.shader.create_from_info(info)

def _create_shader_cp_face()->GPUShader:
	'''Control point shader for face mode.'''
	vertexcode,fragcode=bhqglsl.read_shader_files(directory=INTERN_DIR,filenames=(_B,'cp_face.frag'))
	info=GPUShaderCreateInfo()
	info.vertex_in(0,_C,'P')
	info.push_constant(_D,_E)
	info.push_constant(_A,_F)
	info.uniform_buf(0,CommonParams.__qualname__,_G)
	info.sampler(0,_H,_I)
	info.fragment_out(0,_A,_J)
	info.typedef_source(CommonParams.as_struct())
	info.vertex_source(vertexcode)
	info.fragment_source(fragcode)
	return gpu.shader.create_from_info(info)

def _create_shader_path_edge()->GPUShader:
	'''Path shader for edge mode.'''
	vertexcode,fragcode=bhqglsl.read_shader_files(directory=INTERN_DIR,filenames=(_B,'path_edge.frag'))
	info=GPUShaderCreateInfo()
	info.vertex_in(0,_C,'P')
	info.push_constant(_D,_E)
	info.push_constant(_A,_F)
	info.uniform_buf(0,CommonParams.__qualname__,_G)
	info.sampler(0,_H,_I)
	info.fragment_out(0,_A,_J)
	info.typedef_source(CommonParams.as_struct())
	info.vertex_source(vertexcode)
	info.fragment_source(fragcode)
	return gpu.shader.create_from_info(info)

def _create_shader_path_face()->GPUShader:
	'''Path shader for face mode.'''
	vertexcode,fragcode=bhqglsl.read_shader_files(directory=INTERN_DIR,filenames=(_B,'path_face.frag'))
	info=GPUShaderCreateInfo()
	info.vertex_in(0,_C,'P')
	info.push_constant(_D,_E)
	info.push_constant(_A,_F)
	info.uniform_buf(0,CommonParams.__qualname__,_G)
	info.sampler(0,_H,_I)
	info.fragment_out(0,_A,_J)
	info.typedef_source(CommonParams.as_struct())
	info.vertex_source(vertexcode)
	info.fragment_source(fragcode)
	return gpu.shader.create_from_info(info)

_SHADERS=dict()
def get(name:str)->None|GPUShader:return _SHADERS.get(name,None)
def register():
	_SHADERS['cp_vert']=_create_shader_cp_vert()
	_SHADERS['cp_face']=_create_shader_cp_face()
	_SHADERS['path_edge']=_create_shader_path_edge()
	_SHADERS['path_face']=_create_shader_path_face()
