from .main_plugin import IPBAPlugin


def classFactory(iface):
    return IPBAPlugin(iface)