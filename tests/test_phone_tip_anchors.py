import copy
import json
from pathlib import Path
import unittest
from wuwa_story.phone_tip_anchors import phone_tip_insertions


def fixture():
    action={'Name':'PhoneSystemInteract','Params':{'InteractType':{'Type':'SendPhoneMessage','PhoneRecordActionConfig':{'PhoneMessageId':7}}}}
    node={'Id':2,'ParentNodeId':1,'Type':'ChildQuest','TidTip':'tip','Condition':{'Type':'ReadPhoneMessage','PhoneMessageId':7,'ProgressType':{'Type':'CompleteMessage'}},'TrackCustomBoard':{'TrackPhoneMessageBoard':{'PhoneMessageId':7}},'EnterActions':[action],'FinishActions':[]}
    nodes=[{'Id':1,'ParentNodeId':0,'Type':'Sequence'},node]
    backbone={'order_source':{'entries':[{'TidTip':'tip','Flow':{'FlowListName':'','FlowId':0,'StateId':0}}]},'segments':[]}
    external=[{'node_id':2,'phase':'EnterActions','action_index':0,'source_action':action,'phone':{'message_id':7,'state_key':'p_1_1','missing_text_ids':[],'events':[{'text':'hello'}]}}]
    return nodes,backbone,external


class PhoneTipTests(unittest.TestCase):
    def test_read_step_not_send_time_and_input_unchanged(self):
        n,b,e=fixture();before=copy.deepcopy((n,b,e));out=phone_tip_insertions(n,b,e)
        self.assertEqual(len(out),1);self.assertFalse(out[0]['proof']['runtime_verified'])
        self.assertEqual((n,b,e),before)
    def test_send_only_duplicate_tip_and_async_rejected(self):
        n,b,e=fixture();n[1]['TrackCustomBoard']={};self.assertFalse(phone_tip_insertions(n,b,e))
        n,b,e=fixture();n[1]['Condition']={'Type':'ReachArea'};self.assertFalse(phone_tip_insertions(n,b,e))
        n,b,e=fixture();b['order_source']['entries']*=2;self.assertFalse(phone_tip_insertions(n,b,e))
        n,b,e=fixture();n[1]['EnterActions'][0]['Async']=True;self.assertFalse(phone_tip_insertions(n,b,e))
        n,b,e=fixture();second=copy.deepcopy(n[1]);second['Id']=3;second['EnterActions'][0]['Async']=True;n.append(second)
        self.assertFalse(phone_tip_insertions(n,b,e))
    def test_other_task_duplicate_send_unknown_effect_and_existing_flow_rejected(self):
        n,b,e=fixture();e[0]['node_id']=999;self.assertFalse(phone_tip_insertions(n,b,e))
        n,b,e=fixture();n[1]['FinishActions']=copy.deepcopy(n[1]['EnterActions']);self.assertFalse(phone_tip_insertions(n,b,e))
        n,b,e=fixture();n[1]['FinishActions']=[{'Name':'Unknown','Params':{}}];self.assertFalse(phone_tip_insertions(n,b,e))
        n,b,e=fixture();b['segments']=[{'state_key':'p_1_1'}];self.assertFalse(phone_tip_insertions(n,b,e))
    def test_real_messages_at_distinct_empty_tips(self):
        from wuwa_story.recap_backbone import export_task_backbone
        result=export_task_backbone(165800000)
        out=phone_tip_insertions(result['source']['task_nodes'],result['recap_backbone'],result['external_content'])
        self.assertEqual([(i['entry_index'],i['phone_message_id'],len(i['events'])) for i in out],[(0,32000,14),(5,32001,9)])
        self.assertTrue(all(i['proof']['scope'].startswith('configured reading step') for i in out))


if __name__=='__main__':unittest.main()
