import inspect
import asyncio
from graphlib import TopologicalSorter
from appkit.component import Component
from appkit.service import Service
from typing import Type, Any, Dict


class Bind:
    def __init__(self, cls: Type[Service], *, mode: str = "app"):
        self.cls = cls
        self.mode = mode  # 'app' | 'lazy'
        self._name: str = ""

    def bind_name(self, name: str):
        self._name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        if self.mode == "lazy":
            return self._factory(instance)
        return self

    def _factory(self, app_instance):
        def create_instance(**kwargs):
            deps = inspect.signature(self.cls.create).parameters
            resolved = {
                k: getattr(app_instance, k)
                for k in deps
                if hasattr(app_instance, k)
            }
            resolved.update(kwargs)
            return self.cls(**resolved)
        return create_instance


class App:
    def __init__(self):
        self._components: dict[str, Component] = {}
        self._services: dict[str, Type[Service]] = {}
        self._component_objs: dict[str, Any] = {}
        self._service_objs: dict[str, Any] = {}

        for name, attr in inspect.getmembers(self):
            if isinstance(attr, Component):
                self._components[name] = attr
            elif isinstance(attr, Bind):
                attr.bind_name(name)
                if attr.mode == "app":
                    self._services[name] = attr.cls
                setattr(self, name, attr)

    async def start(self):
        graph = self._build_dependency_graph()
        sorter = TopologicalSorter(graph)

        for name in sorter.static_order():
            if name in self._components:
                component = self._components[name]
                await component.start()
                self._component_objs[name] = component.obj

            elif name in self._services:
                service_cls = self._services[name]
                deps = inspect.signature(service_cls.create).parameters

                kwargs = {
                    k: self._component_objs.get(k) or self._service_objs.get(k)
                    for k in deps
                    if k in self._component_objs or k in self._service_objs
                }

                instance = await service_cls.create(**kwargs)
                self._service_objs[name] = instance
                setattr(self, name, instance)

    async def stop(self):
        for service in reversed(self._service_objs.values()):
            if hasattr(service, 'stop'):
                await service.stop()
        for component in reversed(self._components.values()):
            await component.stop()

    async def is_alive(self) -> dict[str, bool]:
        names = list(self._components.keys())
        coroutines = [component.is_alive for component in self._components.values()]
        results = await asyncio.gather(*coroutines, return_exceptions=True)

        return {name: result is True for name, result in zip(names, results)}

    def _build_dependency_graph(self) -> Dict[str, set[str]]:
        graph: dict[str, set[str]] = {}

        for name, comp in self._components.items():
            deps = comp.dependencies or {}
            graph[name] = set(deps.keys())

        for name, cls in self._services.items():
            deps = inspect.signature(cls.create).parameters
            graph[name] = {
                dep for dep in deps
                if dep in self._components or dep in self._services
            }

        return graph
