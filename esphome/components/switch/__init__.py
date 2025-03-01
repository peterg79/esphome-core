import esphome.codegen as cg
import esphome.config_validation as cv
from esphome import automation
from esphome.automation import Condition, maybe_simple_id
from esphome.components import mqtt
from esphome.const import (
    CONF_DEVICE_CLASS,
    CONF_ENTITY_CATEGORY,
    CONF_ID,
    CONF_INVERTED,
    CONF_MQTT_ID,
    CONF_ON_TURN_OFF,
    CONF_ON_TURN_ON,
    CONF_TRIGGER_ID,
    DEVICE_CLASS_EMPTY,
    DEVICE_CLASS_OUTLET,
    DEVICE_CLASS_SWITCH,
)
from esphome.core import CORE, coroutine_with_priority
from esphome.cpp_generator import MockObjClass
from esphome.cpp_helpers import setup_entity

CODEOWNERS = ["@esphome/core"]
IS_PLATFORM_COMPONENT = True
DEVICE_CLASSES = [
    DEVICE_CLASS_EMPTY,
    DEVICE_CLASS_OUTLET,
    DEVICE_CLASS_SWITCH,
]

switch_ns = cg.esphome_ns.namespace("switch_")
Switch = switch_ns.class_("Switch", cg.EntityBase)
SwitchPtr = Switch.operator("ptr")

ToggleAction = switch_ns.class_("ToggleAction", automation.Action)
TurnOffAction = switch_ns.class_("TurnOffAction", automation.Action)
TurnOnAction = switch_ns.class_("TurnOnAction", automation.Action)
SwitchPublishAction = switch_ns.class_("SwitchPublishAction", automation.Action)

SwitchCondition = switch_ns.class_("SwitchCondition", Condition)
SwitchTurnOnTrigger = switch_ns.class_(
    "SwitchTurnOnTrigger", automation.Trigger.template()
)
SwitchTurnOffTrigger = switch_ns.class_(
    "SwitchTurnOffTrigger", automation.Trigger.template()
)

icon = cv.icon

validate_device_class = cv.one_of(*DEVICE_CLASSES, lower=True)


SWITCH_SCHEMA = cv.ENTITY_BASE_SCHEMA.extend(cv.MQTT_COMMAND_COMPONENT_SCHEMA).extend(
    {
        cv.OnlyWith(CONF_MQTT_ID, "mqtt"): cv.declare_id(mqtt.MQTTSwitchComponent),
        cv.Optional(CONF_INVERTED): cv.boolean,
        cv.Optional(CONF_ON_TURN_ON): automation.validate_automation(
            {
                cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(SwitchTurnOnTrigger),
            }
        ),
        cv.Optional(CONF_ON_TURN_OFF): automation.validate_automation(
            {
                cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(SwitchTurnOffTrigger),
            }
        ),
        cv.Optional(CONF_DEVICE_CLASS): validate_device_class,
    }
)

_UNDEF = object()


def switch_schema(
    class_: MockObjClass = _UNDEF,
    *,
    entity_category: str = _UNDEF,
    device_class: str = _UNDEF,
):
    schema = SWITCH_SCHEMA
    if class_ is not _UNDEF:
        schema = schema.extend({cv.GenerateID(): cv.declare_id(class_)})
    if entity_category is not _UNDEF:
        schema = schema.extend(
            {
                cv.Optional(
                    CONF_ENTITY_CATEGORY, default=entity_category
                ): cv.entity_category
            }
        )
    if device_class is not _UNDEF:
        schema = schema.extend(
            {
                cv.Optional(
                    CONF_DEVICE_CLASS, default=device_class
                ): validate_device_class
            }
        )
    return schema


async def setup_switch_core_(var, config):
    await setup_entity(var, config)

    if CONF_INVERTED in config:
        cg.add(var.set_inverted(config[CONF_INVERTED]))
    for conf in config.get(CONF_ON_TURN_ON, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [], conf)
    for conf in config.get(CONF_ON_TURN_OFF, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [], conf)

    if CONF_MQTT_ID in config:
        mqtt_ = cg.new_Pvariable(config[CONF_MQTT_ID], var)
        await mqtt.register_mqtt_component(mqtt_, config)

    if CONF_DEVICE_CLASS in config:
        cg.add(var.set_device_class(config[CONF_DEVICE_CLASS]))


async def register_switch(var, config):
    if not CORE.has_id(config[CONF_ID]):
        var = cg.Pvariable(config[CONF_ID], var)
    cg.add(cg.App.register_switch(var))
    await setup_switch_core_(var, config)


async def new_switch(config, *args):
    var = cg.new_Pvariable(config[CONF_ID], *args)
    await register_switch(var, config)
    return var


SWITCH_ACTION_SCHEMA = maybe_simple_id(
    {
        cv.Required(CONF_ID): cv.use_id(Switch),
    }
)


@automation.register_action("switch.toggle", ToggleAction, SWITCH_ACTION_SCHEMA)
@automation.register_action("switch.turn_off", TurnOffAction, SWITCH_ACTION_SCHEMA)
@automation.register_action("switch.turn_on", TurnOnAction, SWITCH_ACTION_SCHEMA)
async def switch_toggle_to_code(config, action_id, template_arg, args):
    paren = await cg.get_variable(config[CONF_ID])
    return cg.new_Pvariable(action_id, template_arg, paren)


@automation.register_condition("switch.is_on", SwitchCondition, SWITCH_ACTION_SCHEMA)
async def switch_is_on_to_code(config, condition_id, template_arg, args):
    paren = await cg.get_variable(config[CONF_ID])
    return cg.new_Pvariable(condition_id, template_arg, paren, True)


@automation.register_condition("switch.is_off", SwitchCondition, SWITCH_ACTION_SCHEMA)
async def switch_is_off_to_code(config, condition_id, template_arg, args):
    paren = await cg.get_variable(config[CONF_ID])
    return cg.new_Pvariable(condition_id, template_arg, paren, False)


@coroutine_with_priority(100.0)
async def to_code(config):
    cg.add_global(switch_ns.using)
    cg.add_define("USE_SWITCH")
