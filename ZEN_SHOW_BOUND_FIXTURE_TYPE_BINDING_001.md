# Show-Bound Fixture Type / Channel Profile Binding 001

**Status:** `SHOW_BOUND_VERIFIED`

## Real-console preflight

- Telnet loopback READY: `True` as `MM`.
- Expected Existing Show fingerprint: `497dfae11821c10eebc54a614fa66e81339cb79d789d50c112fcdfc33134f4ea`.
- Fresh loaded-Show fingerprint: `497dfae11821c10eebc54a614fa66e81339cb79d789d50c112fcdfc33134f4ea`.
- Existing Show identity/profile match: `MATCH`.
- Fixture `9999` was not selected, exported, or addressed: `YES`.

## Binding method and provenance

`List Fixture` exact type label -> native `Export FixtureType <id>` -> bounded XML diagnostic -> compound batch identity -> parsed ChannelType/ChannelFunction inventory -> technical-definition SHA-256.
The strict single-export `XML @index == Show pool ID` validator remains unchanged. This verified run establishes the observed `XML @index == requested pool ID - 1` serialization only through its explicit compound identity rule. No name-only local profile match can establish a Show binding.

## Results by current Show FixtureType

### `2 ZEN BAW 20R Mode 2`

- FixtureType numeric ID: `2`.
- Export / provenance state: `SHOW_BOUND_VERIFIED` via `MA2_EXPORT_FIXTURE_TYPE_XML_COMPOUND_IDENTITY`.
- Exact identity verification: `PASS`.
- Failure reason: `none`.
- Technical-definition SHA-256: `4201e4c28154722069b4bdbfb9efcb4a088c62a9e8585e7d4c8eefd2daf19280`.
- XML SHA-256: `09febe05e96a44d310ffbec0aa7e00f245762ba9aa032592598650424f62fc12`.
- Capability classification: COLOR=SHOW_BOUND_VERIFIED, DIMMER=SHOW_BOUND_VERIFIED, FOCUS=SHOW_BOUND_VERIFIED, FROST=SHOW_BOUND_VERIFIED, GOBO=SHOW_BOUND_VERIFIED, PAN=SHOW_BOUND_VERIFIED, PIXEL_SHAPE=UNCLASSIFIED_FROM_CHANNEL_INVENTORY, POSITION=SHOW_BOUND_VERIFIED, PRISM=SHOW_BOUND_VERIFIED, SHUTTER_STROBE=SHOW_BOUND_VERIFIED, TILT=SHOW_BOUND_VERIFIED, ZOOM=SHOW_BOUND_VERIFIED.
- Local profile candidate comparison: `LOCAL_PROFILE_CANDIDATE_UNBOUND`.
- Export diagnostic (retained before temporary cleanup):
- Export filename / request: `ZEN_AGENT_FT_2_ee73aeb6fe14a2ed.xml` / `1789063348250474600`.
- Export feedback: `Executing : Export FixtureType 2 "ZEN_AGENT_FT_2_ee73aeb6fe14a2ed.xml" /nc [Fixture]>`.
- XML root/schema/version: `MA` / `{'major': '3', 'minor': '9', 'stream': '60'}`.
- Exported FixtureType@index: `1`; requested Show pool ID: `2`; exact index match: `False`.
- Exported name/mode: `ZEN BAW 20R` / `Mode 2`; reconstructed against requested List label: `True`.
- Parent/container path: `MA`; FixtureType nodes: `1`; channel count: `32`.
- Diagnostic XML SHA-256: `09febe05e96a44d310ffbec0aa7e00f245762ba9aa032592598650424f62fc12`; normalized technical-definition SHA-256: `4201e4c28154722069b4bdbfb9efcb4a088c62a9e8585e7d4c8eefd2daf19280`.

#### Parsed ChannelType / ChannelFunction inventory

| Index | Attribute | Feature | Preset | Channel Functions |
|---:|---|---|---|---|
| 0 | COLORRGB1 | COLORRGB | COLOR | count=1; attributes=COLORRGB1; subattributes=COLORRGB1 |
| 1 | COLORRGB2 | COLORRGB | COLOR | count=1; attributes=COLORRGB2; subattributes=COLORRGB2 |
| 10 | ANIMATIONINDEXROTATE | GOBOANIMATION | GOBO | count=1; attributes=ANIMATIONINDEXROTATE; subattributes=ANIMATIONROTATE |
| 11 | GOBO2 | GOBO2 | GOBO | count=1; attributes=GOBO2; subattributes=GOBO2 |
| 12 | GOBO2_POS | GOBO2 | GOBO | count=2; attributes=GOBO2_POS; subattributes=GOBO2_POS,GOBO2_ROT |
| 13 | EFFECTWHEEL | EFFECT | BEAM | count=4; attributes=EFFECTMACROPOSITION,EFFECTWHEEL,PRISMA1,PRISMA2; subattributes=EFFECTMACROPOSITION,EFFECTWHEELSELECT,PRISMA1,PRISMA2 |
| 14 | EFFECTINDEXROTATE | EFFECT | BEAM | count=2; attributes=PRISMA1_POS; subattributes=PRISMA1_POS,PRISMA1_ROT |
| 15 | FROST | BEAM1 | BEAM | count=1; attributes=FROST; subattributes=FROST |
| 16 | ZOOM | FOCUS | FOCUS | count=1; attributes=ZOOM; subattributes=ZOOM |
| 17 | FOCUS | FOCUS | FOCUS | count=1; attributes=FOCUS; subattributes=FOCUS |
| 18 | ZOOMMODE | FOCUS | FOCUS | count=2; attributes=ZOOMMODE; subattributes=ZOOMMODENORMAL,ZOOMMODESELECT |
| 19 | PAN | POSITION | POSITION | count=1; attributes=PAN; subattributes=PAN |
| 2 | COLORRGB3 | COLORRGB | COLOR | count=1; attributes=COLORRGB3; subattributes=COLORRGB3 |
| 20 | TILT | POSITION | POSITION | count=1; attributes=TILT; subattributes=TILT |
| 21 | POSITIONMSPEED | MSPEED | CONTROL | count=6; attributes=DUMMY,FOCUSMODE,MACROS,POSITIONMSPEED; subattributes=FOCUSMODESELECT,MACROSELECT,NOFEATURE,POSITIONMSPEEDTRACK |
| 22 | FIXTUREGLOBALRESET | RESET | CONTROL | count=4; attributes=DUMMY,FIXTUREGLOBALRESET,POSITIONRESET,ZOOMRESET; subattributes=FIXTUREGLOBALRESET,NOFEATURE,POSITIONRESET,ZOOMRESET |
| 23 | LAMPCONTROL | LAMP | CONTROL | count=3; attributes=DUMMY,LAMPCONTROL; subattributes=LAMPOFF,LAMPON,NOFEATURE |
| 24 | EFFECTMACROS | EFFECTMACROS | BEAM | count=3; attributes=EFFECTMACRORATE,EFFECTMACROS; subattributes=EFFECTMACRORATE,EFFECTMACROSELECT |
| 25 | VIRTUAL_POSITION_MODE | POSITION | POSITION | count=1; attributes=VIRTUAL_POSITION_MODE; subattributes=VIRTUAL_POSITION_MODE |
| 26 | STAGEX | STAGE | POSITION | count=1; attributes=STAGEX; subattributes=STAGEX |
| 27 | STAGEY | STAGE | POSITION | count=1; attributes=STAGEY; subattributes=STAGEY |
| 28 | STAGEZ | STAGE | POSITION | count=1; attributes=STAGEZ; subattributes=STAGEZ |
| 29 | FLIP | STAGE | POSITION | count=1; attributes=FLIP; subattributes=FLIP |
| 3 | COLOR1 | COLOR1 | COLOR | count=3; attributes=COLOR1,FROST; subattributes=COLOR1,FROST |
| 30 | MARK | STAGE | POSITION | count=1; attributes=MARK; subattributes=MARK |
| 31 | DIST | POSITION | POSITION | count=1; attributes=DIST; subattributes=DIST |
| 4 | COLOR2 | COLOR2 | COLOR | count=1; attributes=COLOR2; subattributes=COLOR2 |
| 5 | COLOR3 | COLOR3 | COLOR | count=1; attributes=COLOR3; subattributes=COLOR3 |
| 6 | SHUTTER | SHUTTER | BEAM | count=7; attributes=SHUTTER; subattributes=SHUTTER,STROBE,STROBEISOPHASE,STROBE_RANDOM |
| 7 | DIM | DIMMER | DIMMER | count=1; attributes=DIM; subattributes=DIM |
| 8 | GOBO1 | GOBO1 | GOBO | count=3; attributes=GOBO1; subattributes=GOBO1,GOBO1_SPIN |
| 9 | ANIMATIONWHEEL | GOBOANIMATION | GOBO | count=1; attributes=ANIMATIONWHEEL; subattributes=ANIMATIONWHEELSELECT |

### `3 ZEN DMH-160 St_Preset`

- FixtureType numeric ID: `3`.
- Export / provenance state: `SHOW_BOUND_VERIFIED` via `MA2_EXPORT_FIXTURE_TYPE_XML_COMPOUND_IDENTITY`.
- Exact identity verification: `PASS`.
- Failure reason: `none`.
- Technical-definition SHA-256: `c6c590aa1cfa715847bd737c9a9202d853129d1d3bf3b8bbc4ef5d947eb71e9f`.
- XML SHA-256: `ce2a091b96b6f5b8dd985d6a1f70e513e826d514bebc61b550736fb0aa62cf26`.
- Capability classification: COLOR=SHOW_BOUND_VERIFIED, DIMMER=SHOW_BOUND_VERIFIED, FOCUS=SHOW_BOUND_VERIFIED, FROST=NOT_PRESENT_IN_EXPORTED_PROFILE, GOBO=SHOW_BOUND_VERIFIED, PAN=SHOW_BOUND_VERIFIED, PIXEL_SHAPE=UNCLASSIFIED_FROM_CHANNEL_INVENTORY, POSITION=SHOW_BOUND_VERIFIED, PRISM=SHOW_BOUND_VERIFIED, SHUTTER_STROBE=SHOW_BOUND_VERIFIED, TILT=SHOW_BOUND_VERIFIED, ZOOM=NOT_PRESENT_IN_EXPORTED_PROFILE.
- Local profile candidate comparison: `LOCAL_PROFILE_CANDIDATE_BOUND`.
- Export diagnostic (retained before temporary cleanup):
- Export filename / request: `ZEN_AGENT_FT_3_2ee713e6d5e31053.xml` / `1789063348969425100`.
- Export feedback: `Executing : Export FixtureType 3 "ZEN_AGENT_FT_3_2ee713e6d5e31053.xml" /nc [Fixture]>`.
- XML root/schema/version: `MA` / `{'major': '3', 'minor': '9', 'stream': '60'}`.
- Exported FixtureType@index: `2`; requested Show pool ID: `3`; exact index match: `False`.
- Exported name/mode: `ZEN DMH-160` / `St_Preset`; reconstructed against requested List label: `True`.
- Parent/container path: `MA`; FixtureType nodes: `1`; channel count: `21`.
- Diagnostic XML SHA-256: `ce2a091b96b6f5b8dd985d6a1f70e513e826d514bebc61b550736fb0aa62cf26`; normalized technical-definition SHA-256: `c6c590aa1cfa715847bd737c9a9202d853129d1d3bf3b8bbc4ef5d947eb71e9f`.

#### Parsed ChannelType / ChannelFunction inventory

| Index | Attribute | Feature | Preset | Channel Functions |
|---:|---|---|---|---|
| 0 | PAN | POSITION | POSITION | count=1; attributes=PAN; subattributes=PAN |
| 1 | TILT | POSITION | POSITION | count=1; attributes=TILT; subattributes=TILT |
| 10 | GOBO1_MODE | GOBO1 | GOBO | count=4; attributes=GOBO1_MODE; subattributes=GOBO1MODEANIMATE,GOBO1MODEINDEX,GOBO1MODEROTATE |
| 11 | GOBO1_POS | GOBO1 | GOBO | count=8; attributes=DUMMY,GOBO1_POS; subattributes=GOBO1ANIMATE,GOBO1_POS,GOBO1_ROT,NOFEATURE |
| 12 | GOBO2WHEELMODE | GOBO2 | GOBO | count=6; attributes=DUMMY,GOBO2WHEELMODE,GOBO2WHEELOFFSETMODE,GOBO2WHEELSELECTBLINK; subattributes=GOBO2WHEELMODECONTINUOUS,GOBO2WHEELMODESPIN,GOBO2WHEELMODEWHOLEGOBOS,GOBO2WHEELSELECTBLINK,GOBO2WHEELSHAKEMODE,NOFEATURE |
| 13 | GOBO2 | GOBO2 | GOBO | count=7; attributes=DUMMY,GOBO2; subattributes=GOBO2,GOBO2_SPIN,NOFEATURE |
| 14 | EFFECTWHEEL | EFFECT | BEAM | count=3; attributes=EFFECTWHEEL,PRISMA1; subattributes=EFFECTWHEELSELECT,PRISMA1 |
| 15 | EFFECTINDEXROTATE | EFFECT | BEAM | count=3; attributes=EFFECTINDEXROTATE,PRISMA1_POS; subattributes=EFFECTROTATE,PRISMA1_ROT |
| 16 | FOCUSMODE | FOCUS | FOCUS | count=2; attributes=FOCUSMODE,UNKNOWN; subattributes=FOCUSMODESELECT,UNKNOWN |
| 17 | FOCUS | FOCUS | FOCUS | count=1; attributes=FOCUS; subattributes=FOCUS |
| 18 | IRISMODE | BEAM1 | BEAM | count=4; attributes=DUMMY,IRISMODE; subattributes=IRISMODE,IRISMODESTROBEPULSECLOSE,IRISMODESTROBEPULSEOPEN,NOFEATURE |
| 19 | IRIS | BEAM1 | BEAM | count=6; attributes=DUMMY,IRIS; subattributes=IRIS,IRIS_STROBE_PULSE_CLOSE,IRIS_STROBE_PULSE_OPEN,NOFEATURE |
| 2 | POSITIONMSPEED | MSPEED | CONTROL | count=1; attributes=POSITIONMSPEED; subattributes=POSITIONMSPEEDTRACK |
| 20 | FIXTUREGLOBALRESET | RESET | CONTROL | count=11; attributes=COLORWHEELRESET,DUMMY,EFFECTWHEELRESET,FIXTUREDISPLAY,FIXTUREGLOBALRESET,FIXTURESLEEP,GOBO1WHEELRESET,POSITIONRESET; subattributes=COLORWHEELRESET,EFFECTWHEELRESET,FIXTUREDISPLAY,FIXTUREGLOBALRESET,FIXTURESHUTDOWN,GOBO1WHEELRESET,NOFEATURE,POSITIONRESET |
| 3 | STROBEMODE | SHUTTER | BEAM | count=4; attributes=STROBEMODE,UNKNOWN; subattributes=STROBEMODE,STROBEMODEPULSE,STROBEMODERANDOM,UNKNOWN |
| 4 | SHUTTER | SHUTTER | BEAM | count=13; attributes=SHUTTER,UNKNOWN; subattributes=SHUTTER,STROBE,STROBE_PULSE,STROBE_RANDOM,UNKNOWN |
| 5 | DIM | DIMMER | DIMMER | count=1; attributes=DIM; subattributes=DIM |
| 6 | COLOR1_MODE | COLOR1 | COLOR | count=6; attributes=COLOR1WHEELOFFSETMODE,COLOR1WHEELSELECTBLINK,COLOR1_MODE,DUMMY; subattributes=COLOR1WHEELMODECONTINUOUS,COLOR1WHEELMODESPIN,COLOR1WHEELMODEWHOLECOLORS,COLOR1WHEELSCANMODE,COLOR1WHEELSELECTBLINK,NOFEATURE |
| 7 | COLOR1 | COLOR1 | COLOR | count=7; attributes=COLOR1,DUMMY; subattributes=COLOR1,COLOR1_SPIN,NOFEATURE |
| 8 | GOBO1WHEELMODE | GOBO1 | GOBO | count=6; attributes=DUMMY,GOBO1WHEELMODE,GOBO1WHEELOFFSETMODE,GOBO1WHEELSELECTBLINK; subattributes=GOBO1WHEELMODECONTINUOUS,GOBO1WHEELMODESPIN,GOBO1WHEELMODEWHOLEGOBOS,GOBO1WHEELSELECTBLINK,GOBO1WHEELSHAKEMODE,NOFEATURE |
| 9 | GOBO1 | GOBO1 | GOBO | count=7; attributes=DUMMY,GOBO1; subattributes=GOBO1,GOBO1_SPIN,NOFEATURE |

### `4 ZEN K10 Shapes`

- FixtureType numeric ID: `4`.
- Export / provenance state: `SHOW_BOUND_VERIFIED` via `MA2_EXPORT_FIXTURE_TYPE_XML_COMPOUND_IDENTITY`.
- Exact identity verification: `PASS`.
- Failure reason: `none`.
- Technical-definition SHA-256: `77b3a0c5a91d0f537879520b5c47a0e570feee288c9b7450068b4084cb5cfce0`.
- XML SHA-256: `edb6fcbb51a63800df53ec81ff109476c081d6fe0648fb284157a59531b7ac1e`.
- Capability classification: COLOR=SHOW_BOUND_VERIFIED, DIMMER=SHOW_BOUND_VERIFIED, FOCUS=SHOW_BOUND_VERIFIED, FROST=NOT_PRESENT_IN_EXPORTED_PROFILE, GOBO=NOT_PRESENT_IN_EXPORTED_PROFILE, PAN=SHOW_BOUND_VERIFIED, PIXEL_SHAPE=UNCLASSIFIED_FROM_CHANNEL_INVENTORY, POSITION=SHOW_BOUND_VERIFIED, PRISM=NOT_PRESENT_IN_EXPORTED_PROFILE, SHUTTER_STROBE=SHOW_BOUND_VERIFIED, TILT=SHOW_BOUND_VERIFIED, ZOOM=SHOW_BOUND_VERIFIED.
- Local profile candidate comparison: `LOCAL_PROFILE_CANDIDATE_UNBOUND`.
- Export diagnostic (retained before temporary cleanup):
- Export filename / request: `ZEN_AGENT_FT_4_16ef1527ca0372d2.xml` / `1789063349671378700`.
- Export feedback: `Executing : Export FixtureType 4 "ZEN_AGENT_FT_4_16ef1527ca0372d2.xml" /nc [Fixture]>`.
- XML root/schema/version: `MA` / `{'major': '3', 'minor': '9', 'stream': '60'}`.
- Exported FixtureType@index: `3`; requested Show pool ID: `4`; exact index match: `False`.
- Exported name/mode: `ZEN K10` / `Shapes`; reconstructed against requested List label: `True`.
- Parent/container path: `MA`; FixtureType nodes: `1`; channel count: `28`.
- Diagnostic XML SHA-256: `edb6fcbb51a63800df53ec81ff109476c081d6fe0648fb284157a59531b7ac1e`; normalized technical-definition SHA-256: `77b3a0c5a91d0f537879520b5c47a0e570feee288c9b7450068b4084cb5cfce0`.

#### Parsed ChannelType / ChannelFunction inventory

| Index | Attribute | Feature | Preset | Channel Functions |
|---:|---|---|---|---|
| 0 | REDALL | COLORDIMALL | COLOR | count=1; attributes=REDALL; subattributes=REDALL |
| 1 | GREENALL | COLORDIMALL | COLOR | count=1; attributes=GREENALL; subattributes=GREENALL |
| 10 | DIMMERCURVE | DIMMER | DIMMER | count=6; attributes=DIMMERCURVE,DUMMY,MACROS,POSITIONMSPEED; subattributes=DIMMERCURVE,MACROSELECT,NOFEATURE,POSITIONMSPEEDTIME,RESERVED |
| 11 | FIXTUREGLOBALRESET | RESET | CONTROL | count=4; attributes=DUMMY,FIXTUREGLOBALRESET,POSITIONRESET,ZOOMRESET; subattributes=FIXTUREGLOBALRESET,NOFEATURE,POSITIONRESET,ZOOMRESET |
| 12 | ZOOM | FOCUS | FOCUS | count=1; attributes=ZOOM; subattributes=ZOOM |
| 13 | COMPOUNDLENSINDEXROTATE | BEAM1 | BEAM | count=5; attributes=COMPOUNDLENSINDEXROTATE,DUMMY; subattributes=COMPOUNDLENSINDEX,COMPOUNDLENSROTATE,NOFEATURE |
| 14 | EFFECTMACROS | EFFECTMACROS | BEAM | count=15; attributes=DUMMY,EFFECTMACROS; subattributes=EFFECTMACROSELECT,NOFEATURE |
| 15 | EFFECTMACRORATE | EFFECTMACROS | BEAM | count=31; attributes=DUMMY,EFFECTMACROPOSITION,EFFECTMACRORATE,EFFECTMACROSIZE; subattributes=EFFECTMACROPOSITION,EFFECTMACRORATE,EFFECTMACROSIZE,NOFEATURE |
| 16 | EFFECTMACROFADETIME | EFFECTMACROS | BEAM | count=18; attributes=DUMMY,EFFECTMACROFADETIME; subattributes=EFFECTMACROFADETIME,NOFEATURE |
| 17 | COLORRGB1 | COLORRGB | COLOR | count=1; attributes=COLORRGB1; subattributes=COLORRGB1 |
| 18 | COLORRGB2 | COLORRGB | COLOR | count=1; attributes=COLORRGB2; subattributes=COLORRGB2 |
| 19 | COLORRGB3 | COLORRGB | COLOR | count=1; attributes=COLORRGB3; subattributes=COLORRGB3 |
| 2 | BLUEALL | COLORDIMALL | COLOR | count=1; attributes=BLUEALL; subattributes=BLUEALL |
| 20 | COLORRGB5 | COLORRGB | COLOR | count=1; attributes=COLORRGB5; subattributes=COLORRGB5 |
| 21 | DIM2 | DIMMER | DIMMER | count=1; attributes=DIM; subattributes=DIM |
| 22 | BACKGROUNDLEVEL | DIMMER | DIMMER | count=1; attributes=BACKGROUNDLEVEL; subattributes=BACKGROUNDLEVEL |
| 23 | EFFECTMACROTIME | EFFECTMACROS | BEAM | count=1; attributes=EFFECTMACROTIME; subattributes=EFFECTMACROTIME |
| 24 | MACROS2 | MACRO | CONTROL | count=29; attributes=MACROS2; subattributes=MACROSELECT2 |
| 25 | FOREGROUNDSHUTTERSTROBE | SHUTTER | BEAM | count=7; attributes=FOREGROUNDSHUTTERSTROBE; subattributes=FOREGROUNDSHUTTER,FOREGROUNDSTROBE,FOREGROUNDSTROBEPULSE,FOREGROUNDSTROBERANDOM |
| 26 | BACKGROUNDSHUTTERSTROBE | SHUTTER | BEAM | count=7; attributes=BACKGROUNDSHUTTERSTROBE; subattributes=BACKGROUNDSHUTTER,BACKGROUNDSTROBE,BACKGROUNDSTROBEPULSE,BACKGROUNDSTROBERANDOM |
| 27 | MACROS3 | MACRO | CONTROL | count=22; attributes=MACROS3; subattributes=MACROSELECT3 |
| 3 | WHITEALL | COLORDIMALL | COLOR | count=1; attributes=WHITEALL; subattributes=WHITEALL |
| 4 | COLORTEMPERATURE | COLORALL | COLOR | count=2; attributes=COLORTEMPERATURE; subattributes=COLORTEMPERATURESELECT,COLOURTEMPERATURECONTROLDISABLED |
| 5 | COLORMIXER | COLORMIX | COLOR | count=2; attributes=COLORMIXER; subattributes=COLORMIXCOLOR,COLORMIXNORMAL |
| 6 | MASTERSHUTTERSTROBE | SHUTTER | BEAM | count=7; attributes=MASTERSHUTTERSTROBE; subattributes=MASTERSHUTTER,MASTERSTROBE,MASTERSTROBEISOPHASE,MASTERSTROBERANDOM |
| 7 | DIM | DIMMER | DIMMER | count=1; attributes=DIM; subattributes=DIM |
| 8 | PAN | POSITION | POSITION | count=1; attributes=PAN; subattributes=PAN |
| 9 | TILT | POSITION | POSITION | count=1; attributes=TILT; subattributes=TILT |

### `5 ZEN MAC AU XB Standard`

- FixtureType numeric ID: `5`.
- Export / provenance state: `SHOW_BOUND_VERIFIED` via `MA2_EXPORT_FIXTURE_TYPE_XML_COMPOUND_IDENTITY`.
- Exact identity verification: `PASS`.
- Failure reason: `none`.
- Technical-definition SHA-256: `b17c21b79419160ca8498a76a06919e1fd5ac920f9ff40f7af9a9671257786d4`.
- XML SHA-256: `4c8ef44bf40ac4175eaa115ed1f580afa309df3060813a2172b53858deab6ebe`.
- Capability classification: COLOR=SHOW_BOUND_VERIFIED, DIMMER=SHOW_BOUND_VERIFIED, FOCUS=SHOW_BOUND_VERIFIED, FROST=NOT_PRESENT_IN_EXPORTED_PROFILE, GOBO=NOT_PRESENT_IN_EXPORTED_PROFILE, PAN=SHOW_BOUND_VERIFIED, PIXEL_SHAPE=UNCLASSIFIED_FROM_CHANNEL_INVENTORY, POSITION=SHOW_BOUND_VERIFIED, PRISM=NOT_PRESENT_IN_EXPORTED_PROFILE, SHUTTER_STROBE=SHOW_BOUND_VERIFIED, TILT=SHOW_BOUND_VERIFIED, ZOOM=SHOW_BOUND_VERIFIED.
- Local profile candidate comparison: `LOCAL_PROFILE_CANDIDATE_BOUND`.
- Export diagnostic (retained before temporary cleanup):
- Export filename / request: `ZEN_AGENT_FT_5_eea859932b6ab0ac.xml` / `1789063350884970800`.
- Export feedback: `Executing : Export FixtureType 5 "ZEN_AGENT_FT_5_eea859932b6ab0ac.xml" /nc [Fixture]>`.
- XML root/schema/version: `MA` / `{'major': '3', 'minor': '9', 'stream': '60'}`.
- Exported FixtureType@index: `4`; requested Show pool ID: `5`; exact index match: `False`.
- Exported name/mode: `ZEN MAC AU XB` / `Standard`; reconstructed against requested List label: `True`.
- Parent/container path: `MA`; FixtureType nodes: `1`; channel count: `21`.
- Diagnostic XML SHA-256: `4c8ef44bf40ac4175eaa115ed1f580afa309df3060813a2172b53858deab6ebe`; normalized technical-definition SHA-256: `b17c21b79419160ca8498a76a06919e1fd5ac920f9ff40f7af9a9671257786d4`.

#### Parsed ChannelType / ChannelFunction inventory

| Index | Attribute | Feature | Preset | Channel Functions |
|---:|---|---|---|---|
| 0 | SHUTTER | SHUTTER | BEAM | count=21; attributes=SHUTTER; subattributes=SHUTTER,STROBE,STROBE_BURST,STROBE_BURST_ELECTRONIC,STROBE_BURST_RANDOM,STROBE_PULSE_CLOSE,STROBE_PULSE_OPEN,STROBE_RANDOM,STROBE_RANDOM_PULSE_CLOSE,STROBE_RANDOM_PULSE_OPEN,STROBE_SINE_ELECTRONIC |
| 1 | DIM | DIMMER | DIMMER | count=1; attributes=DIM; subattributes=DIM |
| 10 | COLORRGB5 | COLORRGB | COLOR | count=1; attributes=COLORRGB5; subattributes=COLORRGB5 |
| 11 | EFFECTMACRORATE | EFFECTMACROS | BEAM | count=2; attributes=COLORTEMPERATURE; subattributes=COLORTEMPERATURE,COLOURTEMPERATURECONTROLDISABLED |
| 12 | EFFECTMACROS | EFFECTMACROS | BEAM | count=1; attributes=EFFECTMACROS; subattributes=EFFECTMACROSELECT |
| 13 | EFFECTWHEEL | EFFECT | BEAM | count=1; attributes=EFFECTWHEEL; subattributes=EFFECTWHEELSELECT |
| 14 | VIRTUAL_POSITION_MODE | POSITION | POSITION | count=1; attributes=VIRTUAL_POSITION_MODE; subattributes=VIRTUAL_POSITION_MODE |
| 15 | STAGEX | STAGE | POSITION | count=1; attributes=STAGEX; subattributes=STAGEX |
| 16 | STAGEY | STAGE | POSITION | count=1; attributes=STAGEY; subattributes=STAGEY |
| 17 | STAGEZ | STAGE | POSITION | count=1; attributes=STAGEZ; subattributes=STAGEZ |
| 18 | FLIP | STAGE | POSITION | count=1; attributes=FLIP; subattributes=FLIP |
| 19 | MARK | STAGE | POSITION | count=1; attributes=MARK; subattributes=MARK |
| 2 | ZOOM | FOCUS | FOCUS | count=1; attributes=ZOOM; subattributes=ZOOM |
| 20 | DIST | POSITION | POSITION | count=1; attributes=DIST; subattributes=DIST |
| 3 | PAN | POSITION | POSITION | count=1; attributes=PAN; subattributes=PAN |
| 4 | TILT | POSITION | POSITION | count=1; attributes=TILT; subattributes=TILT |
| 5 | FIXTUREGLOBALRESET | RESET | CONTROL | count=18; attributes=DIMMERCURVE,DUMMY,FANS,FIXTUREDISPLAY,FIXTUREGLOBALRESET,INTENSITYMODE,POSITIONMSPEED; subattributes=DIMMERCURVE,FANSAUTO,FANSPEED,FIXTUREDISPLAY,FIXTUREGLOBALRESET,INTENSITYMODE,NOFEATURE,POSITIONMSPEEDTRACK |
| 6 | COLORMIXER | COLORMIX | COLOR | count=7; attributes=COLORMIXER,COLORMIXPOSITION; subattributes=COLORMIXCOLOR,COLORMIXCYCLE,COLORMIXNORMAL,COLORMIXPOSITION,COLORMIXRANDOM |
| 7 | COLORRGB1 | COLORRGB | COLOR | count=2; attributes=COLORRGB1,DUMMY; subattributes=COLORRGB1,NOFEATURE |
| 8 | COLORRGB2 | COLORRGB | COLOR | count=2; attributes=COLORRGB2,DUMMY; subattributes=COLORRGB2,NOFEATURE |
| 9 | COLORRGB3 | COLORRGB | COLOR | count=2; attributes=COLORRGB3,DUMMY; subattributes=COLORRGB3,NOFEATURE |

### `6 ZEN LEDPar 9c 9Ch Mode A`

- FixtureType numeric ID: `6`.
- Export / provenance state: `SHOW_BOUND_VERIFIED` via `MA2_EXPORT_FIXTURE_TYPE_XML_COMPOUND_IDENTITY`.
- Exact identity verification: `PASS`.
- Failure reason: `none`.
- Technical-definition SHA-256: `377df06b122685eb9a02c87de9f16b291cbe6b21576d6f09a778465c38d2238e`.
- XML SHA-256: `3065ad6283f5363cb81899f0b22a825a622e838890d742cad2eecc0c6cdf145e`.
- Capability classification: COLOR=SHOW_BOUND_VERIFIED, DIMMER=SHOW_BOUND_VERIFIED, FOCUS=NOT_PRESENT_IN_EXPORTED_PROFILE, FROST=NOT_PRESENT_IN_EXPORTED_PROFILE, GOBO=NOT_PRESENT_IN_EXPORTED_PROFILE, PAN=NOT_PRESENT_IN_EXPORTED_PROFILE, PIXEL_SHAPE=UNCLASSIFIED_FROM_CHANNEL_INVENTORY, POSITION=NOT_PRESENT_IN_EXPORTED_PROFILE, PRISM=NOT_PRESENT_IN_EXPORTED_PROFILE, SHUTTER_STROBE=SHOW_BOUND_VERIFIED, TILT=NOT_PRESENT_IN_EXPORTED_PROFILE, ZOOM=NOT_PRESENT_IN_EXPORTED_PROFILE.
- Local profile candidate comparison: `LOCAL_PROFILE_CANDIDATE_BOUND`.
- Export diagnostic (retained before temporary cleanup):
- Export filename / request: `ZEN_AGENT_FT_6_7a19237580dbf89a.xml` / `1789063351571866000`.
- Export feedback: `Executing : Export FixtureType 6 "ZEN_AGENT_FT_6_7a19237580dbf89a.xml" /nc [Fixture]>`.
- XML root/schema/version: `MA` / `{'major': '3', 'minor': '9', 'stream': '60'}`.
- Exported FixtureType@index: `5`; requested Show pool ID: `6`; exact index match: `False`.
- Exported name/mode: `ZEN LEDPar 9c` / `9Ch Mode A`; reconstructed against requested List label: `True`.
- Parent/container path: `MA`; FixtureType nodes: `1`; channel count: `9`.
- Diagnostic XML SHA-256: `3065ad6283f5363cb81899f0b22a825a622e838890d742cad2eecc0c6cdf145e`; normalized technical-definition SHA-256: `377df06b122685eb9a02c87de9f16b291cbe6b21576d6f09a778465c38d2238e`.

#### Parsed ChannelType / ChannelFunction inventory

| Index | Attribute | Feature | Preset | Channel Functions |
|---:|---|---|---|---|
| 0 | DIM | DIMMER | DIMMER | count=1; attributes=DIM; subattributes=DIM |
| 1 | SHUTTER | SHUTTER | BEAM | count=2; attributes=SHUTTER; subattributes=SHUTTER,STROBE |
| 2 | COLORMIXER | COLORMIX | COLOR | count=2; attributes=COLORMIXER; subattributes=COLORMIXMACROSELECT,COLORMIXNORMAL |
| 3 | COLORMIXMACRORATE | COLORMIX | COLOR | count=1; attributes=COLORMIXMACRORATE; subattributes=COLORMIXMACRORATE |
| 4 | COLORRGB1 | COLORRGB | COLOR | count=1; attributes=COLORRGB1; subattributes=COLORRGB1 |
| 5 | COLORRGB2 | COLORRGB | COLOR | count=1; attributes=COLORRGB2; subattributes=COLORRGB2 |
| 6 | COLORRGB3 | COLORRGB | COLOR | count=1; attributes=COLORRGB3; subattributes=COLORRGB3 |
| 7 | COLORRGB5 | COLORRGB | COLOR | count=1; attributes=COLORRGB5; subattributes=COLORRGB5 |
| 8 | COLORRGB4 | COLORRGB | COLOR | count=1; attributes=COLORRGB4; subattributes=COLORRGB4 |

### `7 Atomic 3000 LED Extended`

- FixtureType numeric ID: `7`.
- Export / provenance state: `SHOW_BOUND_VERIFIED` via `MA2_EXPORT_FIXTURE_TYPE_XML_COMPOUND_IDENTITY`.
- Exact identity verification: `PASS`.
- Failure reason: `none`.
- Technical-definition SHA-256: `b43b56b5c114e661a40ce785bc058b9c5e559f83d7fc75529490efada028bd23`.
- XML SHA-256: `1cf9af9c0c31d7a7215da597a8ed5ba3a3136897abf641824dbe74df848bd2cb`.
- Capability classification: COLOR=SHOW_BOUND_VERIFIED, DIMMER=SHOW_BOUND_VERIFIED, FOCUS=NOT_PRESENT_IN_EXPORTED_PROFILE, FROST=NOT_PRESENT_IN_EXPORTED_PROFILE, GOBO=NOT_PRESENT_IN_EXPORTED_PROFILE, PAN=NOT_PRESENT_IN_EXPORTED_PROFILE, PIXEL_SHAPE=UNCLASSIFIED_FROM_CHANNEL_INVENTORY, POSITION=NOT_PRESENT_IN_EXPORTED_PROFILE, PRISM=NOT_PRESENT_IN_EXPORTED_PROFILE, SHUTTER_STROBE=SHOW_BOUND_VERIFIED, TILT=NOT_PRESENT_IN_EXPORTED_PROFILE, ZOOM=NOT_PRESENT_IN_EXPORTED_PROFILE.
- Local profile candidate comparison: `LOCAL_PROFILE_CANDIDATE_UNBOUND`.
- Export diagnostic (retained before temporary cleanup):
- Export filename / request: `ZEN_AGENT_FT_7_33049e73b694bf84.xml` / `1789063352254858400`.
- Export feedback: `Executing : Export FixtureType 7 "ZEN_AGENT_FT_7_33049e73b694bf84.xml" /nc [Fixture]>`.
- XML root/schema/version: `MA` / `{'major': '3', 'minor': '9', 'stream': '60'}`.
- Exported FixtureType@index: `6`; requested Show pool ID: `7`; exact index match: `False`.
- Exported name/mode: `Atomic 3000 LED` / `Extended`; reconstructed against requested List label: `True`.
- Parent/container path: `MA`; FixtureType nodes: `1`; channel count: `14`.
- Diagnostic XML SHA-256: `1cf9af9c0c31d7a7215da597a8ed5ba3a3136897abf641824dbe74df848bd2cb`; normalized technical-definition SHA-256: `b43b56b5c114e661a40ce785bc058b9c5e559f83d7fc75529490efada028bd23`.

#### Parsed ChannelType / ChannelFunction inventory

| Index | Attribute | Feature | Preset | Channel Functions |
|---:|---|---|---|---|
| 0 | DIM | DIMMER | DIMMER | count=1; attributes=DIM; subattributes=DIM |
| 0 | SHUTTER | SHUTTER | BEAM | count=4; attributes=SHUTTER; subattributes=SHUTTER,STROBE,STROBE_RANDOM |
| 1 | DIM | DIMMER | DIMMER | count=1; attributes=DIM; subattributes=DIM |
| 1 | STROBEDURATION | SHUTTER | BEAM | count=7; attributes=DUMMY,STROBEDURATION; subattributes=NOFEATURE,STROBEDURATION |
| 2 | COLORRGB1 | COLORRGB | COLOR | count=1; attributes=COLORRGB1; subattributes=COLORRGB1 |
| 2 | SHUTTER | SHUTTER | BEAM | count=7; attributes=LIGHTNINGRATE,SHUTTER; subattributes=LIGHTNINGRATE,STROBE,STROBE_PULSE,STROBE_PULSE_CLOSE,STROBE_PULSE_OPEN,STROBE_RANDOM |
| 3 | COLORRGB2 | COLORRGB | COLOR | count=1; attributes=COLORRGB2; subattributes=COLORRGB2 |
| 3 | STROBEMODE | SHUTTER | BEAM | count=7; attributes=STROBEMODE; subattributes=STROBEMODE,STROBEMODELIGHTNING,STROBEMODEPULSE,STROBEMODEPULSECLOSE,STROBEMODEPULSEOPEN,STROBEMODERANDOM |
| 4 | COLORRGB3 | COLORRGB | COLOR | count=1; attributes=COLORRGB3; subattributes=COLORRGB3 |
| 4 | FIXTUREGLOBALRESET | RESET | CONTROL | count=12; attributes=DIMMERCURVE,DUMMY,FANS,FIXTUREDISPLAY,FIXTUREGLOBALRESET,MACROS; subattributes=DIMMERCURVE,FANSAUTO,FANSPEED,FIXTUREDISPLAY,FIXTUREGLOBALRESET,MACROSELECT,NOFEATURE |
| 5 | COLORMIXER | COLORMIX | COLOR | count=3; attributes=COLORMIXER; subattributes=COLORMIXCOLOR,COLORMIXCYCLE,COLORMIXRANDOM |
| 5 | EFFECTMACROS | EFFECTMACROS | BEAM | count=1; attributes=EFFECTMACROS; subattributes=EFFECTMACROSELECT |
| 6 | EFFECTMACRORATE | EFFECTMACROS | BEAM | count=1; attributes=EFFECTMACRORATE; subattributes=EFFECTMACRORATE |
| 7 | EFFECTMACROS2 | EFFECTMACROS | BEAM | count=1; attributes=EFFECTMACROS2; subattributes=EFFECTMACROSELECT2 |

## B3 eligibility and A/B readiness

Show-bound technical capability can support only future case-specific resource eligibility. It does not create a permanent fixture role, case assignment, geometry/position semantics, Effect behavior, or action grammar.
- `REAL_SONG_EXISTING_SHOW_AB_002`: `READY_FOR_CAPABILITY_TO_ROLE_ELIGIBILITY_REVIEW`.
- Reason: All current FixtureType technical definitions are Show-bound; a separate bounded capability-to-role eligibility review remains required before action deltas.

## Safety audit

- MA2 objects modified: `NONE`.
- MA2 object write audit: `ZERO_WRITES`.
- Allowed console transport was Login, List Group, List Fixture, List Preset All and native external `Export FixtureType` only.
- Unexpected commands: `none`.
- Production Designer: `UNCHANGED`; B3: `GUIDANCE_ASSISTED_AB_ONLY`; `ZEN_STYLE_PROFILE`: `DEFERRED`.
