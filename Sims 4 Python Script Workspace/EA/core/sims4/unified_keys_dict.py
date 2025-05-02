from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
class UnifiedKeysManager:
    __slots__ = ('keys_to_indices_cache',)
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UnifiedKeysManager, cls).__new__(cls)
            cls._instance.keys_to_indices_cache = {}
        return cls._instance

    def add_new_tuning_structure_id(self, tuning_structure_key:'Any') -> 'bool':
        if tuning_structure_key not in self.keys_to_indices_cache:
            self.keys_to_indices_cache[tuning_structure_key] = {}
            return True
        return False

class UnifiedKeysDict:
    __slots__ = ('tuning_structure_id', 'tuned_values', 'keys_indices_mapping')

    def __init__(self, initial_dict:'dict', tuning_structure_key:'Any') -> 'None':
        manager = UnifiedKeysManager()
        tuned_values_list = [None]*len(initial_dict)
        is_new_dict = manager.add_new_tuning_structure_id(tuning_structure_key)
        keys_indices_mapping = manager.keys_to_indices_cache[tuning_structure_key]
        counter = 0
        for (key, value) in initial_dict.items():
            if is_new_dict:
                keys_indices_mapping[key] = counter
            tuned_values_list[counter] = value
            counter += 1
        self.tuning_structure_id = tuning_structure_key
        self.tuned_values = tuple(tuned_values_list)
        self.keys_indices_mapping = manager.keys_to_indices_cache[self.tuning_structure_id]

    def __getitem__(self, key:'Any') -> 'Any':
        return self._get_internal(key)

    def __contains__(self, key:'Any'):
        return key in self.keys_indices_mapping

    def __len__(self):
        return len(self.tuned_values)

    def __repr__(self):
        items_preview = ', '.join([f'{repr(k)}: {repr(v)}' for (k, v) in self.items()])
        return f'<UnifiedKeysDict {self.tuning_structure_id} {{items_preview}}>'

    def _get_internal(self, key:'Any', default:'Optional[Any]'=None) -> 'Optional[Any]':
        try:
            index = self.keys_indices_mapping[key]
            return self.tuned_values[index]
        except KeyError as error:
            return default

    def get(self, key:'Any', default:'Optional[Any]'=None):
        return self._get_internal(key, default)

    def items(self) -> 'Iterator[Tuple[Any, Any]]':
        for (key, index) in self.keys_indices_mapping.items():
            yield (key, self.tuned_values[index])
