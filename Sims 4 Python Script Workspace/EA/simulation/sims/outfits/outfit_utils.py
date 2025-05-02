from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from sims.sim_info import SimInfo
    from typing import List, Optional, Setimport itertoolsfrom cas.cas import get_caspart_bodytype, get_tags_from_outfitfrom gsi_handlers import outfit_handlersfrom sims.outfits.outfit_enums import OutfitCategory, CLOTHING_BODY_TYPES, OutfitFilterFlag, BodyType, MatchNotFoundPolicy, BodyTypeFlag, BodyTypeGroupsfrom sims4.hash_util import KEYNAMEMAPTYPE_OBJECTINSTANCESfrom sims4.resources import get_resource_key, get_debug_name, Typesfrom sims4.tuning.tunable import TunableEnumFlags, TunableMapping, TunablePercent
def get_maximum_outfits_for_category(outfit_category):
    if outfit_category == OutfitCategory.BATHING or outfit_category == OutfitCategory.SITUATION:
        return 1
    if outfit_category == OutfitCategory.SPECIAL:
        return 3
    elif outfit_category == OutfitCategory.CAREER:
        return 3
    return 5

def get_tags_present_on_all_given_body_types(body_types_to_intersect:'List', sim_info:'SimInfo', outfit_category:'OutfitCategory', outfit_index:'int') -> 'Set':
    intersection_of_tags = set()
    for body_type in body_types_to_intersect:
        tag_dictionary = get_tags_from_outfit(sim_info._base, outfit_category, outfit_index, body_type_filter=body_type)
        tag_set = set(*tag_dictionary.values())
        intersection_of_tags = intersection_of_tags.intersection(tag_set) if len(intersection_of_tags) > 0 else tag_set
    return intersection_of_tags

def is_sim_info_wearing_all_outfit_parts(sim_info, outfit, outfit_key):
    outfit_data = outfit.get_outfit(*outfit_key)
    current_outfit_data = sim_info.get_outfit(*sim_info.get_current_outfit())
    if current_outfit_data is None:
        return False
    return set(part_id for part_id in outfit_data.part_ids if get_caspart_bodytype(part_id) in CLOTHING_BODY_TYPES).issubset(set(current_outfit_data.part_ids))

def get_cas_part_name(part_id):
    if False:
        return get_debug_name(get_resource_key(part_id, Types.CASPART), table_type=KEYNAMEMAPTYPE_OBJECTINSTANCES)
    return str(part_id)

class OutfitGeneratorRandomizationMixin:
    INSTANCE_TUNABLES = {'filter_flag': TunableEnumFlags(description='\n            Define how to handle part randomization for the generated outfit.\n            ', enum_type=OutfitFilterFlag, default=OutfitFilterFlag.USE_EXISTING_IF_APPROPRIATE | OutfitFilterFlag.USE_VALID_FOR_LIVE_RANDOM, allow_no_flags=True), 'body_type_chance_overrides': TunableMapping(description='\n            Define body type chance overrides for the generate outfit. For\n            example, if BODYTYPE_HAT is mapped to 100%, then the outfit is\n            guaranteed to have a hat if any hat matches the specified tags.\n            \n            If used in an appearance modifier, these body types will contribute\n            to the flags that determine which body types can be generated,\n            regardless of their percent chance.\n            ', key_type=BodyType, value_type=TunablePercent(description='\n                The chance that a part is applied to the corresponding body\n                type.\n                ', default=100)), 'body_type_match_not_found_policy': TunableMapping(description='\n            The policy we should take for a body type that we fail to find a\n            match for. Primary example is to use MATCH_NOT_FOUND_KEEP_EXISTING\n            for generating a tshirt and making sure a sim wearing full body has\n            a lower body cas part.\n            \n            If used in an appearance modifier, these body types will contribute\n            to the flags that determine which body types can be generated.\n            ', key_type=BodyType, value_type=MatchNotFoundPolicy)}
    FACTORY_TUNABLES = INSTANCE_TUNABLES

    def get_body_type_flags(self):
        tuned_flags = 0
        for body_type in itertools.chain(self.body_type_chance_overrides.keys(), self.body_type_match_not_found_policy.keys()):
            tuned_flags |= 1 << body_type
        return tuned_flags or BodyTypeFlag.CLOTHING_ALL

    def get_tuned_required_body_types(self) -> 'Set':
        required_body_types = set()
        for (bodyType, chance) in self.body_type_chance_overrides.items():
            if chance > 0:
                required_body_types.add(bodyType)
        for bodyType in self.body_type_match_not_found_policy.keys():
            required_body_types.add(bodyType)
        return required_body_types.union(BodyTypeGroups.CLOTHING)

    def _generate_outfit(self, sim_info:'SimInfo', outfit_category:'OutfitCategory', outfit_index:'Optional[int]'=0, tag_list:'Optional[Set]'=(), exclude_tag_list:'Optional[Set]'=(), seed:'Optional[int]'=None):
        if outfit_handlers.archiver.enabled:
            outfit_handlers.log_outfit_generate(sim_info, outfit_category, outfit_index, tag_list, exclude_tag_list, self.filter_flag, self.body_type_chance_overrides, self.body_type_match_not_found_policy)
        body_type_flags = BodyTypeFlag.CLOTHING_ALL | self.get_body_type_flags()
        sim_info.generate_outfit(outfit_category, outfit_index=outfit_index, tag_list=tag_list, exclude_tag_list=exclude_tag_list, filter_flag=self.filter_flag, body_type_chance_overrides=self.body_type_chance_overrides, body_type_match_not_found_overrides=self.body_type_match_not_found_policy, seed=seed, body_type_flags=body_type_flags)
