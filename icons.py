from __future__ import annotations
import os
from.import DATA_DIR
from.lib import bhqab
__all__='ICONS_DIRECTORY','DATA_ICON_NAMES','SelectPathIcons','get_id'
ICONS_DIRECTORY=os.path.join(DATA_DIR,'icons')
DATA_ICON_NAMES='appearance','behavior','credits','github','info','keymap','license','links','patreon','preferences','readme','update','youtube'
class SelectPathIcons(bhqab.utils_ui.IconsCache):0
def get_id(identifier:str)->int:SelectPathIcons.initialize(directory=ICONS_DIRECTORY,data_identifiers=DATA_ICON_NAMES,image_identifiers=());return SelectPathIcons.get_id(identifier)