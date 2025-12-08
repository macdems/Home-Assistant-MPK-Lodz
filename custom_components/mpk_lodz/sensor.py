import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import aiohttp
import async_timeout
from homeassistant.components.sensor import ENTITY_ID_FORMAT
from homeassistant.const import CONF_ID, CONF_NAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity, async_generate_entity_id
from homeassistant.util import slugify

from . import _LOGGER
from .const import CONF_DIRECTIONS, CONF_LINES, CONF_STOPNUM, DEFAULT_NAME, DOMAIN, DEVICE_MANUFACTURER


async def async_setup_entry(hass, config_entry, async_add_entities):
    integration_name = config_entry.data.get(CONF_NAME, DEFAULT_NAME)
    for stop_subentry in config_entry.subentries.values():
        stop_data = stop_subentry.data
        stop_id = str(stop_data.get(CONF_ID) or "")
        stop_num = str(stop_data.get(CONF_STOPNUM) or "")
        use_stop_num = not stop_id
        stop = stop_num if use_stop_num else stop_id
        lines = [line for item in stop_data.get(CONF_LINES).split(',') if (line := item.strip())]
        directions = [dir for item in stop_data.get(CONF_DIRECTIONS).split(',') if (dir := item.strip())]
        if use_stop_num:
            stop_name = stop_data.get(CONF_NAME) or f"num_{stop_num}"
        else:
            stop_name = stop_data.get(CONF_NAME) or stop_id
        async_add_entities([MpkLodzSensor(hass, integration_name, stop, use_stop_num, stop_name, lines, directions)],
                           True,
                           config_subentry_id=stop_subentry.subentry_id)


class MpkLodzSensor(Entity):
    icon = "mdi:bus-clock"
    should_poll = True

    def __init__(self, hass, integration_name, stop, use_stop_num, stop_name, lines, directions):
        stop_uid = slugify('{} {}{}'.format(integration_name, "num" if use_stop_num else "", stop))
        uid = "{}_{}".format(integration_name, stop_name)
        if lines: uid += "_" + '_'.join(lines)
        if directions: uid += "_" + '_'.join(directions)
        entity_id = async_generate_entity_id(ENTITY_ID_FORMAT, uid, hass=hass)
        self.entity_id = entity_id
        self._name = integration_name
        self._stop = stop
        self._use_stop_num = use_stop_num
        self._watched_lines = lines
        self._watched_directions = directions
        self._stop_name = stop_name
        self._real_stop_name = None
        self._departures = []
        self._departures_number = 0
        self._departures_by_line = dict()
        self._hass = hass
        self._attr_unique_id = "{}_{}_{}".format(stop_uid, ','.join(lines), ','.join(directions))
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, stop_uid)},
            name=f"{integration_name} - {stop_name}",
            manufacturer=DEVICE_MANUFACTURER,
            configuration_url=f"http://rozklady.lodz.pl/Home/TimeTableReal?stopNum={stop}"
            if use_stop_num else f"http://rozklady.lodz.pl/Home/TimeTableReal?stopId={stop}",
        )

    @property
    def name(self):
        return '{} - {}'.format(self._name, self._stop_name)

    @property
    def state(self):
        if self._departures_number is not None and self._departures_number > 0:
            dep = self._departures[0]
            return MpkLodzSensor.departure_to_str(dep)
        return None

    @property
    def unit_of_measurement(self):
        return None

    @property
    def extra_state_attributes(self):
        attr = dict()
        attr['stop_name'] = self._real_stop_name or self._stop_name
        if self._departures is not None:
            attr['list'] = self._departures
            attr['html_timetable'] = self.get_html_timetable()
            attr['html_departures'] = self.get_html_departures()
            if self._departures_number > 0:
                dep = self._departures[0]
                attr['line'] = dep["line"]
                attr['direction'] = dep["direction"]
                attr['departure'] = dep["departure"]
                attr['time_to_departure'] = dep["time_to_departure"]
        return attr

    async def async_update(self):
        now = datetime.now()
        data = await self.get_data(self._hass, self._stop, self._use_stop_num)
        if data is None:
            return
        self.real_stop_name = data[0].attrib["name"]
        departures = data[0][0]
        parsed_departures = []
        for departure in departures:
            line = departure.attrib["nr"]
            direction = departure.attrib["dir"]
            if self._watched_lines and line not in self._watched_lines \
                    or self._watched_directions and direction not in self._watched_directions:
                continue
            time_in_seconds = int(departure[0].attrib["s"])
            departure = now + timedelta(seconds=time_in_seconds)
            time_to_departure = time_in_seconds // 60
            parsed_departures.append({
                "line": line,
                "direction": direction,
                "departure": "{:02}:{:02}".format(departure.hour, departure.minute),
                "departure_ts": int(departure.timestamp()),
                "time_to_departure": time_to_departure,
            })
        self._departures = parsed_departures
        self._departures_number = len(parsed_departures)
        self._departures_by_line = MpkLodzSensor.group_by_line(self._departures)

    def get_html_timetable(self):
        html = '<table width="100%" border=1 style="border: 1px black solid; border-collapse: collapse;">\n'
        lines = list(self._departures_by_line.keys())
        lines.sort()
        for line in lines:
            directions = list(self._departures_by_line[line].keys())
            directions.sort()
            for direction in directions:
                if len(direction) == 0:
                    continue
                html = html + '<tr><td style="text-align: center; padding: 4px"><big>{}, kier. {}</big></td>'.format(
                    line, direction
                )
                departures = ', '.join(map(lambda x: x["departure"], self._departures_by_line[line][direction]))
                html = html + '<td style="text-align: right; padding: 4px">{}</td></tr>\n'.format(departures)
        if len(lines) == 0:
            html = html + '<tr><td style="text-align: center; padding: 4px">Brak połączeń</td>'
        html = html + '</table>'
        return html

    def get_html_departures(self):
        html = '<table width="100%" border=1 style="border: 1px black solid; border-collapse: collapse;">\n'
        for departure in self._departures:
            html = html + '<tr><td style="text-align: center; padding: 4px">{}</td></tr>\n'.format(
                MpkLodzSensor.departure_to_str(departure)
            )
        html = html + '</table>'
        return html

    @staticmethod
    def departure_to_str(dep):
        return '{}, kier. {}: {} ({}m)'.format(dep["line"], dep["direction"], dep["departure"], dep["time_to_departure"])

    @staticmethod
    def group_by_line(departures):
        departures_by_line = dict()
        for departure in departures:
            line = departure["line"]
            direction = departure["direction"]
            if line not in departures_by_line:
                departures_by_line[line] = dict()
            if direction not in departures_by_line[line]:
                departures_by_line[line][direction] = []
            departures_by_line[line][direction].append(departure)
        return departures_by_line

    @staticmethod
    async def get_stop_name(hass, stop, use_stop_num):
        data = await MpkLodzSensor.get_data(hass, stop, use_stop_num)
        if data is None:
            return None
        return data[0].attrib["name"]

    @staticmethod
    async def get_data(hass, stop, use_stop_num):
        address = "http://rozklady.lodz.pl/Home/GetTimeTableReal?busStopId={}".format(stop)
        if use_stop_num:
            address = "http://rozklady.lodz.pl/Home/GetTimeTableReal?busStopNum={}".format(stop)
        session = async_get_clientsession(hass)
        try:
            async with async_timeout.timeout(10):
                async with session.get(address) as response:
                    if response.status != 200:
                        _LOGGER.error("Error fetching data: %s", response.status)
                        return None
                    text = await response.text()
                    if not text:
                        _LOGGER.error("Empty response from %s", address)
                        return None
                    return ET.fromstring(text)
        except aiohttp.ClientError as err:
            _LOGGER.error("Connection error: %s", err)
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout error while fetching data from %s", address)
