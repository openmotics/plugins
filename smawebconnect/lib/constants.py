URL_LOGIN = "/dyn/login.json"
URL_LOGOUT = "/dyn/logout.json"
URL_VALUES = "/dyn/getValues.json"
URL_ALL_VALUES = "/dyn/getAllOnlValues.json"
URL_ALL_PARAMS = "/dyn/getAllParamValues.json"
URL_LOGGER = "/dyn/getLogger.json"
URL_DASH_LOGGER = "/dyn/getDashLogger.json"
URL_DASH_VALUES = "/dyn/getDashValues.json"

ELECTRIC_POTENTIAL = 'electric_potential'
ELECTRIC_CURRENT = 'electric_current'
FREQUENCY = 'frequency'
ENERGY = 'energy'
POWER = 'power'


from dataclasses import dataclass
from gateway.enums import SensorEnums, MeasurementEnums
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class SensorMapping:
    name: str
    description: str
    physical_quantity: str
    unit: str
    factor: float
    value: float = None


@dataclass
class CounterMapping:
    name: str
    description: str
    category: MeasurementEnums.Category
    type: MeasurementEnums.Type
    factor: float
    is_injection: bool
    value: float = None


@dataclass
class FieldMappingInstance:
    sensor_key: str
    sensor_mapping: SensorMapping
    counter_key: str
    counter_mapping: CounterMapping

    def get_external_id(self):
        if self.sensor_key is not None:
            sensor_name = f"{self.sensor_key}_{self.sensor_mapping.name}"
        else:
            sensor_name = None
        if self.counter_key is not None:
            counter_name = f"{self.counter_key}_{self.counter_mapping.name}"
        else:
            counter_name = None

        return '_'.join([x for x in [sensor_name, counter_name] if x is not None])
    

class FieldMapping:
    def __init__(self):
        self.registry = {}
        self.sensor_to_counter_link = {}
        self.counter_to_sensor_link = {}
        self.initialize()

    def initialize(self):
        self.register_mapping(
            sensor_key='6100_40263F00',
            sensor_mapping=SensorMapping(
                name='grid_power',
                description='Grid power',
                physical_quantity=SensorEnums.PhysicalQuantities.POWER,
                unit=SensorEnums.Units.WATT,
                factor=1.0),
            counter_key='6400_00260100',
            counter_mapping=CounterMapping(
                name='total_yield',
                description='Total yield',
                category=MeasurementEnums.Category.ELECTRIC,
                type=MeasurementEnums.Type.SOLAR,
                is_injection=True,
                factor=1000.0)
        )
        self.register_mapping(
            sensor_key='6100_00465700',
            sensor_mapping=SensorMapping(
                name='frequency',
                description='Frequency',
                physical_quantity=SensorEnums.PhysicalQuantities.FREQUENCY,
                unit=SensorEnums.Units.HERTZ,
                factor=100.0)
        )
        self.register_mapping(
            sensor_key='6100_00464800',
            sensor_mapping=SensorMapping(
                name='voltage_l1',
                description='Voltage L1',
                physical_quantity=SensorEnums.PhysicalQuantities.ELECTRIC_POTENTIAL,
                unit=SensorEnums.Units.VOLT,
                factor=100.0)
        )
        self.register_mapping(
            sensor_key='6100_00464900',
            sensor_mapping=SensorMapping(
                name='voltage_l2',
                description='Voltage L2',
                physical_quantity=SensorEnums.PhysicalQuantities.ELECTRIC_POTENTIAL,
                unit=SensorEnums.Units.VOLT,
                factor=100.0))
        self.register_mapping(
            sensor_key='6100_00464A00',
            sensor_mapping=SensorMapping(
                name='voltage_l3',
                description='Voltage L3',
                physical_quantity=SensorEnums.PhysicalQuantities.ELECTRIC_POTENTIAL,
                unit=SensorEnums.Units.VOLT,
                factor=100.0))
        self.register_mapping(
            sensor_key='6100_40465300',
            sensor_mapping=SensorMapping(
                name='current_l1',
                description='Current L1',
                physical_quantity=SensorEnums.PhysicalQuantities.ELECTRIC_CURRENT,
                unit=SensorEnums.Units.AMPERE,
                factor=1000.0))
        self.register_mapping(
            sensor_key='6100_40465400',
            sensor_mapping=SensorMapping(
                name='current_l2',
                description='Current L2',
                physical_quantity=SensorEnums.PhysicalQuantities.ELECTRIC_CURRENT,
                unit=SensorEnums.Units.AMPERE,
                factor=1000.0))
        self.register_mapping(
            sensor_key='6100_40465500',
            sensor_mapping=SensorMapping(
                name='current_l3',
                description='Current L3',
                physical_quantity=SensorEnums.PhysicalQuantities.ELECTRIC_CURRENT,
                unit=SensorEnums.Units.AMPERE,
                factor=1000.0))
        self.register_mapping(
            sensor_key='6100_0046C200',
            sensor_mapping=SensorMapping(
                name='pv_power',
                description='PV power',
                physical_quantity=SensorEnums.PhysicalQuantities.POWER,
                unit=SensorEnums.Units.WATT,
                factor=1.0),
            counter_key='6400_0046C300',
            counter_mapping=CounterMapping(
                name='pv_gen_meter',
                description='PV generation meter',
                category=MeasurementEnums.Category.ELECTRIC,
                type=MeasurementEnums.Type.OTHER,
                is_injection=True,
                factor=1000.0))
        self.register_mapping(
            sensor_key='6380_40451F00',
            sensor_mapping=SensorMapping(
                name='pv_voltage',
                description='PV voltage (average of all PV channels)',
                physical_quantity=SensorEnums.PhysicalQuantities.ELECTRIC_POTENTIAL,
                unit=SensorEnums.Units.VOLT,
                factor=100.0))
        self.register_mapping(
            sensor_key='6380_40452100',
            sensor_mapping=SensorMapping(
                name='pv_current',
                description='PV current (average of all PV channels)',
                physical_quantity=SensorEnums.PhysicalQuantities.ELECTRIC_CURRENT,
                unit=SensorEnums.Units.AMPERE,
                factor=1000.0))
        self.register_mapping(
            sensor_key='6100_40463600',
            sensor_mapping=SensorMapping(
                name='grid_power_supplied',
                description='Grid power supplied',
                physical_quantity=SensorEnums.PhysicalQuantities.POWER,
                unit=SensorEnums.Units.WATT,
                factor=1.0),
            counter_key='6400_00462400',
            counter_mapping=CounterMapping(
                name='grid_total_yield',
                description='Grid total yield',
                category=MeasurementEnums.Category.ELECTRIC,
                type=MeasurementEnums.Type.OTHER,
                is_injection=True,
                factor=1000.0))
        self.register_mapping(
            sensor_key='6100_40463700',
            sensor_mapping=SensorMapping(
                name='grid_power_absorbed',
                description='Grid power absorbed',
                physical_quantity=SensorEnums.PhysicalQuantities.POWER,
                unit=SensorEnums.Units.WATT,
                factor=1.0),
            counter_key='6400_00462500',
            counter_mapping=CounterMapping(
                name='grid_total_absorbed',
                description='Grid total absorbed',
                category=MeasurementEnums.Category.ELECTRIC,
                type=MeasurementEnums.Type.OTHER,
                is_injection=False,
                factor=1000.0))
        self.register_mapping(
            sensor_key='6100_00543100',
            sensor_mapping=SensorMapping(
                name='current_consumption',
                description='Current consumption',
                physical_quantity=SensorEnums.PhysicalQuantities.POWER,
                unit=SensorEnums.Units.WATT,
                factor=1.0),
            counter_key='6400_00543A00',
            counter_mapping=CounterMapping(
                name='total_consumption',
                description='Total consumption',
                category=MeasurementEnums.Category.ELECTRIC,
                type=MeasurementEnums.Type.OTHER,
                is_injection=False,
                factor=1000.0))
        self.register_mapping(
            counter_key='6400_00262200',
            counter_mapping=CounterMapping(
                name='daily_yield',
                description='Daily yield',
                category=MeasurementEnums.Category.ELECTRIC,
                type=MeasurementEnums.Type.OTHER,
                is_injection=True,
                factor=1000.0))

    def register_mapping(self, sensor_key=None, sensor_mapping=None, counter_key=None, counter_mapping=None):
        if sensor_key is not None and sensor_mapping is not None:
            self.registry[sensor_key] = sensor_mapping
        if counter_key is not None and counter_mapping is not None:
            self.registry[counter_key] = counter_mapping
        if sensor_key is not None and counter_key is not None:
            self.sensor_to_counter_link[sensor_key] = counter_key
            self.counter_to_sensor_link[counter_key] = sensor_key

    def get_all_mappings(self) -> List[FieldMappingInstance]:
        mappings = []
        seen_keys = []
        for key in self.registry.keys():
            if key in seen_keys:
                continue
            mapping = self.get_mapping(key)
            if mapping is None:
                continue
            mappings.append(mapping)
            if mapping.sensor_key is not None:
                seen_keys.append(mapping.sensor_key)
            if mapping.counter_key is not None:
                seen_keys.append(mapping.counter_key)
        return mappings

    def get_mapping(self, key: str) -> Optional[FieldMappingInstance]:
        if key not in self.registry:
            return None
        mapping = self.registry[key]

        sensor_key = None
        sensor_mapping = None
        counter_key = None
        counter_mapping = None

        if isinstance(mapping, SensorMapping):
            sensor_key = key
            sensor_mapping = mapping
            if key in self.sensor_to_counter_link:
                counter_key = self.sensor_to_counter_link[key]
                counter_mapping = self.registry[counter_key]
        if isinstance(mapping, CounterMapping):
            counter_mapping = mapping
            if key in self.counter_to_sensor_link:
                sensor_key = self.counter_to_sensor_link[key]
                sensor_mapping = self.registry[sensor_key]

        result = FieldMappingInstance(
            sensor_key=sensor_key,
            sensor_mapping=sensor_mapping,
            counter_key=counter_key,
            counter_mapping=counter_mapping)
        return result





# FIELD_MAPPING = {'6100_40263F00': {'name': 'grid_power',
#                                    'description': 'Grid power',
#                                    'physical_quantity': 'power',
#                                    'unit': 'watt',
#                                    'type': 'gauge',
#                                    'factor': 1.0},
#                  '6100_00465700': {'name': 'frequency',
#                                    'description': 'Frequency',
#                                    'physical_quantity': 'frequency',
#                                    'unit': 'hertz',
#                                    'type': 'gauge',
#                                    'factor': 100.0},
#                  '6100_00464800': {'name': 'voltage_l1',
#                                    'description': 'Voltage L1',
#                                    'physical_quantity': 'electric_potential',
#                                    'unit': 'volt',
#                                    'type': 'gauge',
#                                    'factor': 100.0},
#                  '6100_00464900': {'name': 'voltage_l2',
#                                    'description': 'Voltage L2',
#                                    'physical_quantity': 'electric_potential',
#                                    'unit': 'volt',
#                                    'type': 'gauge',
#                                    'factor': 100.0},
#                  '6100_00464A00': {'name': 'voltage_l3',
#                                    'description': 'Voltage L3',
#                                    'physical_quantity': 'electric_potential',
#                                    'unit': 'volt',
#                                    'type': 'gauge',
#                                    'factor': 100.0},
#                  '6100_40465300': {'name': 'current_l1',
#                                    'description': 'Current L1',
#                                    'physical_quantity': 'electric_current',
#                                    'unit': 'ampere',
#                                    'type': 'gauge',
#                                    'factor': 1000.0},
#                  '6100_40465400': {'name': 'current_l2',
#                                    'description': 'Current L2',
#                                    'physical_quantity': 'electric_current',
#                                    'unit': 'ampere',
#                                    'type': 'gauge',
#                                    'factor': 1000.0},
#                  '6100_40465500': {'name': 'current_l3',
#                                    'description': 'Current L3',
#                                    'physical_quantity': 'electric_current',
#                                    'unit': 'ampere',
#                                    'type': 'gauge',
#                                    'factor': 1000.0},
#                  '6100_0046C200': {'name': 'pv_power',
#                                    'description': 'PV power',
#                                    'physical_quantity': 'power',
#                                    'unit': 'watt',
#                                    'type': 'gauge',
#                                    'factor': 1.0},
#                  '6380_40451F00': {'name': 'pv_voltage',
#                                    'description': 'PV voltage (average of all PV channels)',
#                                    'physical_quantity': 'electric_potential',
#                                    'unit': 'volt',
#                                    'type': 'gauge',
#                                    'factor': 100.0},
#                  '6380_40452100': {'name': 'pv_current',
#                                    'description': 'PV current (average of all PV channels)',
#                                    'physical_quantity': 'electric_current',
#                                    'unit': 'ampere',
#                                    'type': 'gauge',
#                                    'factor': 1000.0},
#                  '6400_0046C300': {'name': 'pv_gen_meter',
#                                    'description': 'PV generation meter',
#                                    'physical_quantity': 'energy',
#                                    'unit': 'kilo_watt_hour',
#                                    'type': 'counter',
#                                    'factor': 1000.0},
#                  '6400_00260100': {'name': 'total_yield',
#                                    'description': 'Total yield',
#                                    'physical_quantity': 'energy',
#                                    'unit': 'kilo_watt_hour',
#                                    'type': 'counter',
#                                    'factor': 1000.0},
#                  '6400_00262200': {'name': 'daily_yield',
#                                    'description': 'Daily yield',
#                                    'physical_quantity': 'energy',
#                                    'unit': 'kilo_watt_hour',
#                                    'type': 'counter',
#                                    'factor': 1000.0},
#                  '6100_40463600': {'name': 'grid_power_supplied',
#                                    'description': 'Grid power supplied',
#                                    'physical_quantity': 'power',
#                                    'unit': 'watt',
#                                    'type': 'gauge',
#                                    'factor': 1.0},
#                  '6100_40463700': {'name': 'grid_power_absorbed',
#                                    'description': 'Grid power absorbed',
#                                    'physical_quantity': 'power',
#                                    'unit': 'watt',
#                                    'type': 'gauge',
#                                    'factor': 1.0},
#                  '6400_00462400': {'name': 'grid_total_yield',
#                                    'description': 'Grid total yield',
#                                    'physical_quantity': 'energy',
#                                    'unit': 'kilo_watt_hour',
#                                    'type': 'counter',
#                                    'factor': 1000.0},
#                  '6400_00462500': {'name': 'grid_total_absorbed',
#                                    'description': 'Grid total absorbed',
#                                    'physical_quantity': 'energy',
#                                    'unit': 'kilo_watt_hour',
#                                    'type': 'counter',
#                                    'factor': 1000.0},
#                  '6100_00543100': {'name': 'current_consumption',
#                                    'description': 'Current consumption',
#                                    'physical_quantity': 'power',
#                                    'unit': 'watt',
#                                    'type': 'gauge',
#                                    'factor': 1.0},
#                  '6400_00543A00': {'name': 'total_consumption',
#                                    'description': 'Total consumption',
#                                    'physical_quantity': 'energy',
#                                    'unit': 'kilo_watt_hour',
#                                    'type': 'counter',
#                                    'factor': 1000.0}}
