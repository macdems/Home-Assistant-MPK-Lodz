[![HACS Custom][hacs_shield]][hacs]
[![GitHub Latest Release][releases_shield]][latest_release]
[![GitHub All Releases][downloads_total_shield]][releases]


[hacs_shield]: https://img.shields.io/static/v1.svg?label=HACS&message=Custom&style=popout&color=orange&labelColor=41bdf5&logo=HomeAssistantCommunityStore&logoColor=white
[hacs]: https://hacs.xyz/docs/faq/custom_repositories

[latest_release]: https://github.com/macdems/Home-Assistant-MPK-Lodz/releases/latest
[releases_shield]: https://img.shields.io/github/release/macdems/Home-Assistant-MPK-Lodz.svg?style=popout

[releases]: https://github.com/macdems/Home-Assistant-MPK-Lodz/releases
[downloads_total_shield]: https://img.shields.io/github/downloads/macdems/Home-Assistant-MPK-Lodz/total


# MPK Łódź sensor

This sensor uses unofficial API provided by MPK Łódź.

## Installation

### Using [HACS](https://hacs.xyz/) (recommended)

This integration can be added to HACS as a [custom repository](https://hacs.xyz/docs/faq/custom_repositories):
* URL: `https://github.com/macdems/Home-Assistant-MPK-Lodz`
* Category: `Integration`

After adding a custom repository you can use HACS to install this integration using user interface.

### Manual

To install this integration manually you have to download [*mpk_lodz.zip*](https://github.com/macdems/Home-Assistant-MPK-Lodz/releases/latest/download/mpk_lodz.zip) and extract its contents to `config/custom_components/mpk_lodz` directory:
```bash
mkdir -p custom_components/mpk_lodz
cd custom_components/mpk_lodz
wget https://github.com/macdems/Home-Assistant-MPK-Lodz/releases/latest/download/mpk_lodz.zip
unzip mpk_lodz.zip
rm mpk_lodz.zip
```

## Configuration

* To add the "**MPK Łódź**" integration click this button:
  
  [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=mpk_lodz).

  Alternatively, you may use Settings -> Devices & Services -> Add Integration and select **MPK Łódź** from the list.

* Specify the service name. It will impact the default prefix of your entities.

* In the integration page click **Add stop** and fill in stop details (see below).


### Stop configuration

First, you need to get the value of a stop ID or its number. It can be retrieved from [*ITS Łódź*](http://rozklady.lodz.pl/). After choosing a desired stop open its electronical table. There should be a number visibile in URL. If URL contains `busStopId` you should use this number as *Stop ID*. If URL contains `busStopNum` you should use this number as *Stop number*. 

In the stop configuration dialog, you must fill-in exactly one of:

* *Stop ID* — ID of a stop.
* *Stop number* - stop number.

In addition, you may specify optional parameters.

* *Stop name* — stop name. If omitted, it will be retrieved automatically
* *Lines* — comma-separated list of monitored lines.
* *Directions* — comma-separated list of monitored directions.

You may add the same stop multiple times with different monitored lines. This will create multiple entities for monitored stops.

## Hints

These sensors provides attributes which can be used in [*HTML card*](https://github.com/PiotrMachowski/Home-Assistant-Lovelace-HTML-card) or [*HTML Template card*](https://github.com/PiotrMachowski/Home-Assistant-Lovelace-HTML-Template-card): `html_timetable`, `html_departures`

* HTML card:
  ```yaml
  - type: custom:html-card
    title: 'MPK'
    content: |
      <big><center>Timetable</center></big>
      [[ sensor.mpk_lodz_2427.attributes.html_timetable ]]
      <big><center>Departures</center></big>
      [[ sensor.mpk_lodz_2873.attributes.html_departures ]]
  ```
* HTML Template card:
  ```yaml
  - type: custom:html-template-card
    title: 'MPK'
    ignore_line_breaks: true
    content: |
      <big><center>Timetable</center></big></br>
      {{ state_attr('sensor.mpk_lodz_2427','html_timetable') }}
      </br><big><center>Departures</center></big></br>
      {{ state_attr('sensor.mpk_lodz_2873','html_departures') }}
  ```
