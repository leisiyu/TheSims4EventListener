from protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom objects.components import Component, types, componentmethod, componentmethod_with_fallbackfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInitimport sims4.callback_utilsimport sims4.loglogger = sims4.log.Logger('BrandingComponent', default_owner='javier.canon')
class BrandingIconComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=types.BRANDING_ICON_COMPONENT, persistence_key=protocols.PersistenceMaster.PersistableData.BrandingIconComponent, allow_dynamic=True):
    FACTORY_TUNABLES = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._icon = None
        self._on_icon_changed = None

    def save(self, persistence_master_message):
        persistable_data = protocols.PersistenceMaster.PersistableData()
        persistable_data.type = protocols.PersistenceMaster.PersistableData.BrandingIconComponent
        branding_icon_component_data = persistable_data.Extensions[protocols.PersistableBrandingIconComponent.persistable_data]
        if self._icon is not None:
            branding_icon_component_data.icon = sims4.resources.get_protobuff_for_key(self._icon)
        persistence_master_message.data.extend([persistable_data])

    def load(self, persistable_data):
        branding_icon_component_data = persistable_data.Extensions[protocols.PersistableBrandingIconComponent.persistable_data]
        if branding_icon_component_data.HasField('icon'):
            icon_data = branding_icon_component_data.icon
            icon = sims4.resources.Key(icon_data.type, icon_data.instance, icon_data.group)
            self.set_icon(icon)

    @componentmethod_with_fallback(lambda : False)
    def has_icon(self):
        if self._icon:
            return True
        return False

    @componentmethod
    def get_icon(self):
        return self._icon

    @componentmethod
    def set_icon(self, icon):
        self._icon = icon
        self._call_icon_changed_callback()
        return True

    @componentmethod
    def remove_icon(self):
        self.set_icon(None)

    @componentmethod_with_fallback(lambda *_, **__: None)
    def add_icon_changed_callback(self, callback):
        if self._on_icon_changed is None:
            self._on_icon_changed = sims4.callback_utils.CallableList()
        self._on_icon_changed.append(callback)

    @componentmethod_with_fallback(lambda *_, **__: None)
    def remove_icon_changed_callback(self, callback):
        if callback in self._on_icon_changed:
            self._on_icon_changed.remove(callback)
            if not self._on_icon_changed:
                self._on_icon_changed = None

    def _call_icon_changed_callback(self):
        if self._on_icon_changed is not None:
            self._on_icon_changed(self.owner)
