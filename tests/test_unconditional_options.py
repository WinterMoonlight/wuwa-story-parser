import copy
import unittest
from wuwa_story.unconditional_options import candidate_indices, select_option, selection_evidence, preflight_walk


def guarded():
    return {'TidTalkOption':'conditional', 'PreCondition':{'Type':'Condition', 'Conditions':{
        'Type':0,'Conditions':[{'Type':'CheckItems','Compare':'Ge','Items':[{'ItemId':1,'Count':1}]}]}}}


class UnconditionalOptionsTests(unittest.TestCase):
    def test_original_indices_loop_and_explicit_guard_rejected(self):
        options=[guarded(),{'TidTalkOption':'one'},{'TidTalkOption':'two'}]
        before=copy.deepcopy(options)
        self.assertEqual(candidate_indices(options),[1,2])
        self.assertEqual(select_option(options),1)
        self.assertEqual(select_option(options,tried={1}),2)
        self.assertEqual(select_option(options,override=2),2)
        for index in [0,-1,3,True,'1']:
            with self.assertRaises(ValueError):select_option(options,override=index)
        with self.assertRaises(ValueError):select_option(options,tried={1,2})
        with self.assertRaises(ValueError):select_option([guarded()])
        self.assertEqual(options,before)
        e=selection_evidence(options)
        self.assertEqual(e['excluded_original_indices'],[0])
        self.assertFalse(e['condition_values_evaluated'])
        e['source_conditions'][0]['condition']['Type']='changed'
        self.assertEqual(options,before)

    def test_only_option_guard_is_skipped(self):
        option=guarded();option['Actions']=[{'Name':'Bad','Params':{'Condition':{'Type':'Unknown'}}}]
        item={'Id':1,'Options':[option], 'PreCondition':{'Type':'Unknown'}}
        before=copy.deepcopy(item);objects=list(preflight_walk([item]))
        self.assertIn(item,objects)
        self.assertTrue(any('Condition' in o for o in objects))
        self.assertFalse(any(o.get('Type')=='CheckItems' for o in objects))
        self.assertEqual(item,before)
        bad=guarded();bad['PreCondition']['Conditions']['Type']=True
        with self.assertRaises(ValueError):list(preflight_walk([{'Options':[bad]}]))
        bad=guarded();bad['OtherCondition']={}
        with self.assertRaises(ValueError):candidate_indices([bad])

    def test_compare_guard_unknown_initial_value_is_not_evaluated(self):
        option=guarded();option['PreCondition']['Conditions']['Conditions']=[{
            'Type':'CompareVar','Var1':{'Type':'Boolean','Source':'Self','Name':'unset'},
            'Compare':'Eq','Var2':{'Type':'Boolean','Source':'Constant','Value':False}}]
        self.assertEqual(candidate_indices([option,{}]),[1])
        self.assertFalse(selection_evidence([option,{}])['condition_values_evaluated'])
        option['PreCondition']['Conditions']['Conditions'][0]['Compare']='Ne'
        with self.assertRaises(ValueError):candidate_indices([option,{}])
