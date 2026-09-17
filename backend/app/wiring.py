import importlib

# Модули, которые при импорте подписывают обработчики на event_bus.
HANDLER_MODULES: tuple[str, ...] = ("app.modules.directories.handlers",)


def register_event_handlers() -> None:
    for module_name in HANDLER_MODULES:
        importlib.import_module(module_name)
