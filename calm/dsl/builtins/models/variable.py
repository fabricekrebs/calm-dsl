from .entity import EntityType, Entity
from .validator import PropertyValidator


# Variable

class VariableType(EntityType):
    __schema_name__ = "Variable"


class VariableValidator(PropertyValidator, openapi_type="variable"):
    __default__ = None
    __kind__ = VariableType


def _var(**kwargs):
    name = getattr(VariableType, "__schema_name__")
    bases = (Entity, )
    return VariableType(name, bases, kwargs)


def var_type(cls):
    name = cls.__name__
    bases = (Entity, )
    kwargs = dict(cls.__dict__) # class dict is mappingproxy
    return VariableType(name, bases, kwargs)


Variable = _var()


def setvar(name, value, **kwargs):

    kwargs["name"] = name
    kwargs["value"] = value

    name = name.title() + getattr(VariableType, "__schema_name__")
    return VariableType(name, (Entity, ), kwargs)


def var(value, **kwargs):
    name = getattr(VariableType, "__schema_name__")
    return setvar(name, value, **kwargs)
