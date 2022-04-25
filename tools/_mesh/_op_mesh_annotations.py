from typing import Union, Literal
from bmesh.types import BMVert, BMEdge, BMFace


class MeshOperatorVariables:
    # Tool settings mesh select modes and mesh elements
    initial_ts_msm: tuple[Union[int, bool], Union[int, bool], Union[int, bool]]
    initial_mesh_elements: Literal['verts', 'edges', 'faces']

    prior_ts_msm: tuple[Union[int, bool], Union[int, bool], Union[int, bool]]
    prior_mesh_elements: str

    select_ts_msm: tuple[Union[int, bool], Union[int, bool], Union[int, bool]]
    select_mesh_elements: str

    # Initial selected mesh elements
    initial_select: tuple[Union[BMVert, BMEdge, BMFace]]
