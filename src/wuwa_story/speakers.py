from .database import rows, integer, texts


def anonymous(name):
    return bool(name) and set(name.strip()) <= {'?', '？'}


class SpeakerResolver:
    def __init__(self, records=None):
        if records is not None:
            self.records = records
            self.actors = []
            return
        lang = {r['Id']: r['Content'] for r in rows('zh-Hans/lang_speaker.db', 'Speaker')}
        self.records = {}
        for row in rows('db_speaker.db', 'speaker'):
            # This client's speaker FlatBuffer field 3 is the legacy Name index.
            candidates = [('NameStringKey', row['NameStringKey']),
                          ('BinData.Name(field3)', integer(row['BinData'], 3))]
            result = {'name': '', 'source': 'unresolved'}
            for source, index in candidates:
                if index < 0 or index not in lang:
                    continue
                raw = lang[index]
                name = texts.get(raw, raw)
                if name and not name.startswith('Speaker_'):
                    result = {'name': name, 'source': source, 'language_index': index,
                              'raw_name': raw}
                    break
            self.records[row['Id']] = result
        self.actors = []

    def begin(self, params, evidence):
        self.actors = []
        for index, actor in enumerate(params.get('Actors', [])):
            sid = actor.get('TalkerId', -1)
            name = self.records.get(sid, {}).get('name', '')
            self.actors.append({'actor_index': index, 'entity_id': actor.get('EntityId'),
                                'talker_id': sid, 'known_speaker_id': sid if name and not anonymous(name) else None,
                                'evidence': [evidence]})

    def change(self, params, evidence):
        index = params['ActorIndex']
        if index < 0 or index >= len(self.actors):
            return False
        actor = self.actors[index]
        sid = params['Talker']
        actor['talker_id'] = sid
        actor['evidence'] = actor['evidence'] + [evidence]
        name = self.records.get(sid, {}).get('name', '')
        if name and not anonymous(name):
            actor['known_speaker_id'] = sid
        return True

    def identify(self, sid):
        record = self.records.get(sid, {'name': '', 'source': 'unresolved'})
        name = record['name'] or ('旁白' if sid is None else '未知说话人')
        result = {'speaker_id': sid, 'display_name': name, 'name_source': record,
                  'resolved_speaker_id': None, 'resolved_name': None,
                  'identity_status': 'unresolved' if anonymous(name) or not record['name'] else 'display_name_only'}
        if anonymous(name):
            candidates = [a for a in self.actors if a['talker_id'] == sid]
            # A shared anonymous label must never select an arbitrary actor.
            if len(candidates) == 1 and candidates[0]['known_speaker_id'] is not None:
                actor = candidates[0]
                known = actor['known_speaker_id']
                result.update(resolved_speaker_id=known, resolved_name=self.records[known]['name'],
                              identity_status='config_actor_continuity', evidence=dict(actor))
        return result
