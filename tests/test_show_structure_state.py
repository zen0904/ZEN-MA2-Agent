import unittest
import tempfile
from pathlib import Path
from shutil import copytree

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.parser import parse
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.state.providers.layouts import LayoutExportProvider
from zen_ma2_agent.state.providers.sequences import CueProvider, SequenceProvider
from zen_ma2_agent.state.providers.show_pools import EffectProvider, ExecutorProvider, PageProvider, PresetProvider
from zen_ma2_agent.telnet_client import ConnectionState


LAYOUT_XML = '''<MA xmlns="http://schemas.malighting.de/grandma2/xml/MA"><Group index="0" name="Stage"><LayoutData><CObjects>
<LayoutCObject center_x="-320.5" center_y="140.25" size_w="80" size_h="80" rotation="15" fix_id="101"><CObject name="Key" /></LayoutCObject>
<LayoutCObject center_x="3.5" center_y="-2.25" size_w="1" size_h="2" group_no="1"><CObject name="HYBRID" /></LayoutCObject>
</CObjects></LayoutData></Group></MA>'''


class ShowStructureProviderTests(unittest.TestCase):
    def test_layout_xml_preserves_negative_float_fixture_group_and_empty_items(self):
        layout=LayoutExportProvider.parse(LAYOUT_XML,1)
        self.assertEqual({key:layout["items"][0][key] for key in ("type","reference","name","x","y","w","h","rotation","export_order")}, {"type":"fixture","reference":101,"name":"Key","x":-320.5,"y":140.25,"w":80.0,"h":80.0,"rotation":15.0,"export_order":0})
        self.assertTrue(layout["items"][0]["resolved"])
        self.assertEqual(layout["items"][1]["type"],"group")
        empty=LayoutExportProvider.parse('<MA><Group index="0" name="Empty"><LayoutData><CObjects /></LayoutData></Group></MA>',1)
        self.assertEqual(empty["items"],[])
        with self.assertRaises(ValueError): LayoutExportProvider.parse('<MA><Group index="1"><LayoutData /></Group></MA>',1)
        with self.assertRaises(Exception): LayoutExportProvider.parse('<MA>',1)

    def test_sequence_cues_timing_and_sparse_numbers(self):
        self.assertEqual([item.number for item in SequenceProvider().parse('Sequence 5 "Song"\nSequence 101 "Encore"')],[5,101])
        cues=CueProvider().parse('Cue 1 "Intro" Trigger: Go Fade: 2.5 Delay: 0.1\nCue 3.5 "Hit"',5)
        self.assertEqual((cues[0].number,cues[0].name,cues[0].trigger,cues[0].fade,cues[0].delay),(1,"Intro","Go",2.5,0.1))
        self.assertEqual(cues[1].number,3.5)
        self.assertEqual(CueProvider().parse('No cues',5),[])

    def test_preset_effect_page_executor_inventory(self):
        presets=PresetProvider().parse('Preset 4.1 "Front"\nPreset 4.4 "Back"','POSITION')
        self.assertEqual([item["number"] for item in presets],[1,4])
        self.assertEqual(PresetProvider().parse('', 'GOBO'),[])
        effects=EffectProvider().parse('Effect 10 "Pan Wave" Template Lines: 3 Attributes: Position, Tilt\nEffect 99 "Flash"')
        self.assertEqual(effects[0]["attributes"],["Position","Tilt"])
        self.assertEqual(effects[1]["number"],99)
        self.assertEqual(PageProvider().parse('Page 1 "Main"\nPage 5 "Song"')[1]["name"],"Song")
        executors=ExecutorProvider().parse('Executor 1.201 Sequence 5 "Song 01"\nExec 1.202 Effect 10 "Pan"\nExecutor 1.203')
        self.assertEqual(executors[0]["assignment"],5)
        self.assertEqual(executors[1]["assignment_type"],"effect")
        self.assertIsNone(executors[2]["assignment_type"])

    def test_chat_intents_auto_request_state_dependencies(self):
        self.assertEqual(parse('有哪些 Position Preset？').kind,'preset_list')
        self.assertEqual(parse('有哪些 Color Preset？').parameters,{"preset_type":"COLOR"})
        self.assertEqual(parse('有哪些 Effect？').kind,'effect_list')
        self.assertEqual(parse('Effect 10 是什麼？').kind,'effect_lookup')
        self.assertEqual(parse('Sequence 5 掛在哪個 Executor？').kind,'sequence_executor_lookup')
        self.assertEqual(parse('Page 1 有哪些 Executor？').kind,'page_executor_list')
        self.assertEqual(parse('Layout 1 裡有哪些燈？').kind,'layout_items_query')
        self.assertEqual(parse('Layout 1 裡有哪些燈？').parameters,{"layout_no":1})
        self.assertEqual(parse('HYBRID 在 Layout 1 怎麼排？').parameters,{"layout_no":1,"object_name":"HYBRID"})

    def test_preset_provider_uses_the_read_only_allow_list(self):
        class Client:
            def __init__(self, *_args): self.state=ConnectionState.DISCONNECTED; self.authenticated_user=None; self.audit_entries=[]; self.commands=[]
            def connect(self, username, password=""): self.state=ConnectionState.READY; self.authenticated_user=username; return "ready"
            def execute(self, command): self.commands.append(command); return ""
            def close(self): self.state=ConnectionState.DISCONNECTED
        with tempfile.TemporaryDirectory(prefix="zen-preset-") as temporary:
            root=Path(temporary); copytree(Path(__file__).resolve().parents[1] / "skills",root / "skills")
            runtime=AgentRuntime(root,client_factory=Client); core=AgentCore(runtime); core.connect("127.0.0.1",30000,"MM","")
            response=core.handle_request("有哪些 Position Preset？")
            self.assertEqual(response["type"],"ANSWER")
            self.assertEqual(response["message"],"Position Presets (0)\nNo entries returned.")
            self.assertEqual(runtime.client.commands,["List Preset Position"])


if __name__ == '__main__': unittest.main()
