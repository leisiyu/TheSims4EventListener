import enum
class OutfitOverrideOptionFlags(enum.IntFlags):
    DEFAULT = 0
    OVERRIDE_ALL_OUTFITS = 1
    IGNORE_BATHING = 2
    MANNEQUIN_MODE = 4
    APPLY_MODIFIER_VARIATION = 8
    FROM_SCRATCH = 16
    APPLY_GENETICS_FROM_OVERRIDE = 32
    OVERRIDE_CUSTOM_TEXTURES = 64
    OVERRIDE_HAIR_MATCH_FLAGS = 128
    OVERRIDE_SKIP_UI_CHECKS = 256
    SKIP_BODY_MODIFICATIONS = 512
    APPLY_IN_CURRENT_MODIFIED_SIM_INFO = 1024
    OVERRIDE_TATTOO_CUSTOM_TEXTURES = 2048
try:
    import _cas
except:

    class _cas:
        SimInfo = None
        OutfitData = None

        @staticmethod
        def age_up_sim(*_, **__):
            pass

        @staticmethod
        def get_buffs_from_part_ids(*_, **__):
            return []

        @staticmethod
        def get_tags_from_outfit(*_, **__):
            return set()

        @staticmethod
        def generate_offspring(*_, **__):
            pass

        @staticmethod
        def generate_household(*_, **__):
            pass

        @staticmethod
        def generate_merged_outfit(*_, **__):
            pass

        @staticmethod
        def generate_random_siminfo(*_, **__):
            pass

        @staticmethod
        def generate_occult_siminfo(*_, **__):
            pass

        @staticmethod
        def is_duplicate_merged_outfit(*_, **__):
            pass

        @staticmethod
        def is_online_entitled(*_, **__):
            pass

        @staticmethod
        def apply_siminfo_override(*_, **__):
            pass

        @staticmethod
        def randomize_part_color(*_, **__):
            pass

        @staticmethod
        def randomize_skintone_from_tags(*_, **__):
            pass

        @staticmethod
        def set_caspart(*_, **__):
            pass

        @staticmethod
        def remove_caspart(*_, **__):
            pass

        @staticmethod
        def revert_modifiers_override(*_, **__):
            pass

        @staticmethod
        def dump_active_modifiers(*_, **__):
            pass

        @staticmethod
        def randomize_caspart(*_, **__):
            pass

        @staticmethod
        def randomize_caspart_list(*_, **__):
            pass

        @staticmethod
        def get_catalog_casparts_by_bodytype(*_, **__):
            pass

        @staticmethod
        def remove_caspart_by_bodytype(*_, **__):
            pass

        @staticmethod
        def get_caspart_bodytype(*_, **__):
            pass

        @staticmethod
        def caspart_has_tag(*_, **__):
            pass

        @staticmethod
        def relgraph_set_edge(*_, **__):
            pass

        @staticmethod
        def relgraph_get_genealogy(*_, **__):
            pass

        @staticmethod
        def relgraph_set_marriage(*_, **__):
            pass

        @staticmethod
        def relgraph_set_engagement(*_, **__):
            pass

        @staticmethod
        def relgraph_add_child(*_, **__):
            pass

        @staticmethod
        def relgraph_get(*_, **__):
            pass

        @staticmethod
        def relgraph_set(*_, **__):
            pass

        @staticmethod
        def relgraph_cull(*_, **__):
            pass

        @staticmethod
        def change_bodytype_level(*_, **__):
            pass

        @staticmethod
        def get_caspart_gender_compatible(*_, **__):
            pass

        @staticmethod
        def get_caspart_hide_occult_flags(*_, **__):
            pass
BaseSimInfo = _cas.SimInfoOutfitData = _cas.OutfitDataage_up_sim = _cas.age_up_simget_buff_from_part_ids = _cas.get_buffs_from_part_idsget_tags_from_outfit = _cas.get_tags_from_outfitgenerate_offspring = _cas.generate_offspringgenerate_household = _cas.generate_householdgenerate_merged_outfit = _cas.generate_merged_outfitgenerate_random_siminfo = _cas.generate_random_siminfogenerate_occult_siminfo = _cas.generate_occult_siminfois_duplicate_merged_outfit = _cas.is_duplicate_merged_outfitis_online_entitled = _cas.is_online_entitledapply_siminfo_override = _cas.apply_siminfo_overriderandomize_part_color = _cas.randomize_part_colorrandomize_skintone_from_tags = _cas.randomize_skintone_from_tagsset_caspart = _cas.set_caspartrandomize_caspart = _cas.randomize_caspartrandomize_caspart_list = _cas.randomize_caspart_listget_caspart_bodytype = _cas.get_caspart_bodytypecaspart_has_tag = _cas.caspart_has_tagrelgraph_set_edge = _cas.relgraph_set_edgerelgraph_get_genealogy = _cas.relgraph_get_genealogyrelgraph_set_marriage = _cas.relgraph_set_marriagerelgraph_set_engagement = _cas.relgraph_set_engagementrelgraph_add_child = _cas.relgraph_add_childrelgraph_get = _cas.relgraph_getrelgraph_set = _cas.relgraph_setrelgraph_cull = _cas.relgraph_cullchange_bodytype_level = _cas.change_bodytype_levelget_caspart_gender_compatible = _cas.get_caspart_gender_compatibleget_caspart_hide_occult_flags = _cas.get_caspart_hide_occult_flagsremove_caspart = _cas.remove_caspartrevert_modifiers_override = _cas.revert_modifiers_overridedump_active_modifiers = _cas.dump_active_modifiersget_catalog_casparts_by_bodytype = _cas.get_catalog_casparts_by_bodytyperemove_caspart_by_bodytype = _cas.remove_caspart_by_bodytype